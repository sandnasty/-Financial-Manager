"""Least-privilege runtime secret access without secret-value persistence."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping

AuditSink = Callable[[dict[str, str]], None]
_VALID_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


class SecretAccessError(PermissionError):
    """Raised when a service is not allowed to retrieve a secret."""


class SecretUnavailableError(RuntimeError):
    """Raised when an authorized runtime secret has not been injected."""


@dataclass(frozen=True, slots=True)
class SecretPolicy:
    name: str
    environments: frozenset[str]
    authorized_services: frozenset[str]
    rotation_days: int
    live_execution: bool = False


class SecretValue:
    """Opaque wrapper that prevents accidental display in logs or exceptions."""

    __slots__ = ("__value",)

    def __init__(self, value: str) -> None:
        self.__value = value

    def reveal(self) -> str:
        """Reveal only at the narrow provider/client integration boundary."""
        return self.__value

    def __repr__(self) -> str:
        return "SecretValue('[REDACTED]')"

    def __str__(self) -> str:
        return "[REDACTED]"


def load_policy(path: Path) -> dict[str, SecretPolicy]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    policies: dict[str, SecretPolicy] = {}
    for item in raw["secrets"]:
        name = str(item["name"])
        if not _VALID_NAME.fullmatch(name):
            raise ValueError(f"invalid secret name: {name}")
        policies[name] = SecretPolicy(
            name=name,
            environments=frozenset(map(str, item["environments"])),
            authorized_services=frozenset(map(str, item["authorized_services"])),
            rotation_days=int(item["rotation_days"]),
            live_execution=bool(item.get("live_execution", False)),
        )
    return policies


class EnvironmentSecretStore:
    """Read explicitly allowlisted secrets injected into the process environment."""

    def __init__(
        self,
        *,
        service_id: str,
        environment: str,
        policies: Mapping[str, SecretPolicy],
        audit: AuditSink,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.service_id = service_id
        self.environment = environment.lower()
        self.policies = policies
        self.audit = audit
        self.environ = os.environ if environ is None else environ
        self._revoked: set[str] = set()

    def _record(self, name: str, result: str, reason: str) -> None:
        self.audit(
            {
                "action": "secret.access",
                "actor_id": self.service_id,
                "environment": self.environment,
                "secret_name": name,
                "result": result,
                "reason": reason,
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )

    def get(self, name: str) -> SecretValue:
        policy = self.policies.get(name)
        if policy is None:
            self._record(name, "denied", "unknown-secret")
            raise SecretAccessError("secret is not declared")
        if self.environment not in policy.environments:
            self._record(name, "denied", "environment-not-authorized")
            raise SecretAccessError("secret is not authorized in this environment")
        if self.service_id not in policy.authorized_services:
            self._record(name, "denied", "service-not-authorized")
            raise SecretAccessError("service is not authorized for this secret")
        if policy.live_execution and ("agent" in self.service_id or "llm" in self.service_id):
            self._record(name, "denied", "agent-live-secret-boundary")
            raise SecretAccessError("AI/LLM services cannot access live execution secrets")
        if name in self._revoked:
            self._record(name, "denied", "revoked")
            raise SecretAccessError("secret has been revoked")
        variable = f"FM_{self.environment.upper()}_{name}"
        value = self.environ.get(variable)
        if not value:
            self._record(name, "unavailable", "not-injected")
            raise SecretUnavailableError("authorized secret is not available at runtime")
        self._record(name, "allowed", "policy-authorized")
        return SecretValue(value)

    def revoke(self, name: str, *, operator_role: str) -> None:
        if operator_role != "authorized-operator":
            self._record(name, "denied", "revocation-not-authorized")
            raise SecretAccessError("only an authorized operator may revoke secrets")
        self._revoked.add(name)
        self.audit(
            {
                "action": "secret.revoked",
                "actor_id": operator_role,
                "environment": self.environment,
                "secret_name": name,
                "result": "success",
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )
