"""Canonical immutable audit events and PostgreSQL-backed storage."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

_REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(api[_-]?key|authorization|cookie|credential|password|private[_-]?key|"
    r"secret|token|account_number|connection[_-]?string)",
    re.IGNORECASE,
)


def redact(value: Any) -> Any:
    """Recursively remove prohibited values before persistence."""
    if isinstance(value, dict):
        return {
            str(key): _REDACTED if _SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for integrity hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Canonical event shared by APIs, agents, policy, and brokerage adapters."""

    event_id: UUID
    occurred_at: datetime
    actor_id: str
    actor_type: str
    action: str
    target_type: str
    target_id: str
    correlation_id: str
    trace_id: str
    result: str
    source_service: str
    source_version: str
    environment: str
    immutable_refs: dict[str, str] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, **values: Any) -> "AuditEvent":
        values.setdefault("event_id", uuid4())
        values.setdefault("occurred_at", datetime.now(UTC))
        values["details"] = redact(values.get("details", {}))
        return cls(**values)

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["event_id"] = str(self.event_id)
        value["occurred_at"] = self.occurred_at.astimezone(UTC).isoformat()
        return value


class Connection(Protocol):
    """Small DB-API boundary; production injects a PostgreSQL connection."""

    def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> Any: ...


class PostgresAuditStore:
    """Append events through the only application-granted database function."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def append(self, event: AuditEvent) -> str:
        payload = event.payload()
        digest = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        cursor = self.connection.execute(
            "SELECT audit.append_event(%s::jsonb, %s)",
            (canonical_json(payload), digest),
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("audit append returned no event identifier")
        return str(row[0])

    def reconstruct(self, correlation_id: str) -> list[dict[str, Any]]:
        cursor = self.connection.execute(
            "SELECT event_payload FROM audit.events "
            "WHERE correlation_id = %s ORDER BY sequence_number",
            (correlation_id,),
        )
        return [row[0] for row in cursor.fetchall()]
