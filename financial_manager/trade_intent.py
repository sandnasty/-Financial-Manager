"""Authenticated TradeIntent boundary between recommendations and execution."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from uuid import UUID

from financial_manager.audit import canonical_json
from financial_manager.controls import OperationalControls

AuditSink = Callable[[dict[str, Any]], None]
RiskPolicy = Callable[["TradeIntent"], bool]
VerifyCapability = Callable[["SignedTradeIntent"], bool]
_INSTRUMENT = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")
_REQUIRED_PROVENANCE = {"recommendation_event_id", "risk_decision_event_id", "source_version"}


class TradeIntentRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TradeIntent:
    schema_version: str
    intent_id: str
    correlation_id: str
    instrument: str
    side: str
    quantity: str
    sizing_basis: str
    order_constraints: dict[str, Any]
    strategy_thesis_ref: str
    risk_policy_version: str
    approval_state: str
    approval_id: str
    approver_id: str
    issued_at: datetime
    expires_at: datetime
    provenance: dict[str, str]

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["issued_at"] = self.issued_at.astimezone(UTC).isoformat()
        value["expires_at"] = self.expires_at.astimezone(UTC).isoformat()
        return value

    def validate(self, *, now: datetime) -> None:
        try:
            UUID(self.intent_id)
            quantity = Decimal(self.quantity)
        except (ValueError, InvalidOperation) as exc:
            raise TradeIntentRejected("invalid identifier or quantity") from exc
        if self.schema_version != "1.0":
            raise TradeIntentRejected("unsupported TradeIntent schema")
        if not self.correlation_id or not _INSTRUMENT.fullmatch(self.instrument):
            raise TradeIntentRejected("invalid correlation or instrument")
        if self.side not in {"BUY", "SELL"} or quantity <= 0:
            raise TradeIntentRejected("invalid side or quantity")
        if not self.sizing_basis or not self.strategy_thesis_ref or not self.risk_policy_version:
            raise TradeIntentRejected("missing decision reference")
        if self.approval_state != "approved" or not self.approval_id or not self.approver_id:
            raise TradeIntentRejected("explicit human approval is required")
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None or now.tzinfo is None:
            raise TradeIntentRejected("timestamps must be timezone-aware")
        if self.expires_at <= now or self.expires_at <= self.issued_at:
            raise TradeIntentRejected("TradeIntent is stale or expired")
        if self.expires_at - self.issued_at > timedelta(minutes=15):
            raise TradeIntentRejected("TradeIntent lifetime exceeds 15 minutes")
        if not _REQUIRED_PROVENANCE.issubset(self.provenance):
            raise TradeIntentRejected("incomplete provenance")


@dataclass(frozen=True, slots=True)
class SignedTradeIntent:
    intent: TradeIntent
    key_id: str
    algorithm: str
    signature: str


class ApprovalSigningBoundary:
    """Signing/verification capability held only by the approval service.

    The broker receives `verify`, not key material. HMAC-SHA-256 is the initial
    authenticated mechanism; the key is obtained through the MS-61 runtime
    secret boundary and may be replaced by a managed asymmetric signer without
    changing the TradeIntent or gateway contract.
    """

    def __init__(self, *, service_id: str, key_id: str, key: bytes) -> None:
        if service_id != "approval-service":
            raise PermissionError("only approval-service may hold the signing capability")
        if len(key) < 32:
            raise ValueError("signing key must contain at least 256 bits")
        self.key_id = key_id
        self.__key = key

    def sign(self, intent: TradeIntent, *, operator_role: str) -> SignedTradeIntent:
        if operator_role != "authorized-operator" or intent.approval_state != "approved":
            raise PermissionError("authorized human approval is required before signing")
        body = canonical_json(intent.payload()).encode()
        signature = base64.urlsafe_b64encode(hmac.digest(self.__key, body, "sha256")).decode()
        return SignedTradeIntent(intent, self.key_id, "HS256", signature)

    def verify(self, envelope: SignedTradeIntent) -> bool:
        if envelope.algorithm != "HS256" or envelope.key_id != self.key_id:
            return False
        expected = hmac.digest(self.__key, canonical_json(envelope.intent.payload()).encode(), "sha256")
        try:
            supplied = base64.urlsafe_b64decode(envelope.signature.encode())
        except ValueError:
            return False
        return hmac.compare_digest(expected, supplied)


class BrokerGatewayBoundary:
    def __init__(
        self,
        *,
        verify: VerifyCapability,
        risk_policy: RiskPolicy,
        controls: OperationalControls,
        audit: AuditSink,
    ) -> None:
        self.verify = verify
        self.risk_policy = risk_policy
        self.controls = controls
        self.audit = audit
        self._consumed: dict[str, tuple[str, str]] = {}

    def accept(
        self, envelope: SignedTradeIntent, *, caller_service: str, now: datetime
    ) -> str:
        intent = envelope.intent
        payload_digest = hashlib.sha256(canonical_json(intent.payload()).encode()).hexdigest()
        previous = self._consumed.get(intent.intent_id)
        if previous:
            previous_digest, order_ref = previous
            if previous_digest == payload_digest and self.verify(envelope):
                return order_ref
            raise TradeIntentRejected("intent identifier replayed with altered or invalid content")
        if caller_service != "approval-service":
            raise TradeIntentRejected("direct agent-to-broker path is prohibited")
        intent.validate(now=now)
        if not self.verify(envelope):
            raise TradeIntentRejected("signature verification failed")
        self.controls.require_action("trade-intent.submit")
        if not self.risk_policy(intent):
            raise TradeIntentRejected("current risk policy rejected TradeIntent")
        order_ref = f"accepted:{intent.intent_id}"
        self._consumed[intent.intent_id] = (payload_digest, order_ref)
        self.audit(
            {
                "action": "trade-intent.accepted",
                "actor_id": caller_service,
                "target_id": intent.intent_id,
                "correlation_id": intent.correlation_id,
                "approval_id": intent.approval_id,
                "approver_id": intent.approver_id,
                "recommendation_event_id": intent.provenance["recommendation_event_id"],
                "risk_decision_event_id": intent.provenance["risk_decision_event_id"],
                "result": "accepted",
                "occurred_at": now.astimezone(UTC).isoformat(),
            }
        )
        return order_ref
