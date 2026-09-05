from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from financial_manager.controls import OperationalControls
from financial_manager.trade_intent import (
    ApprovalSigningBoundary,
    BrokerGatewayBoundary,
    TradeIntent,
    TradeIntentRejected,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 5, 18, 0, tzinfo=UTC)


def intent(**changes: object) -> TradeIntent:
    base = TradeIntent(
        schema_version="1.0",
        intent_id=str(uuid4()),
        correlation_id="corr-100",
        instrument="NVDA",
        side="BUY",
        quantity="2",
        sizing_basis="approved-share-count",
        order_constraints={"order_type": "limit", "limit_price": "170.00"},
        strategy_thesis_ref="thesis-100",
        risk_policy_version="risk-v1",
        approval_state="approved",
        approval_id="approval-100",
        approver_id="human-operator-1",
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
        provenance={
            "recommendation_event_id": "event-recommend-100",
            "risk_decision_event_id": "event-risk-100",
            "source_version": "0.1.0",
        },
    )
    return replace(base, **changes)


class TradeIntentBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[dict[str, object]] = []
        self.signing = ApprovalSigningBoundary(
            service_id="approval-service", key_id="dev-key-1", key=b"k" * 32
        )
        self.controls = OperationalControls(self.events.append)
        self.gateway = BrokerGatewayBoundary(
            verify=self.signing.verify,
            risk_policy=lambda _: True,
            controls=self.controls,
            audit=self.events.append,
        )

    def signed(self, value: TradeIntent):
        return self.signing.sign(value, operator_role="authorized-operator")

    def test_valid_approved_intent_is_accepted_and_audit_chain_is_linked(self):
        value = intent()
        ref = self.gateway.accept(self.signed(value), caller_service="approval-service", now=NOW)
        self.assertEqual(ref, f"accepted:{value.intent_id}")
        event = self.events[-1]
        self.assertEqual(event["approval_id"], "approval-100")
        self.assertEqual(event["recommendation_event_id"], "event-recommend-100")
        self.assertEqual(event["risk_decision_event_id"], "event-risk-100")

    def test_only_approval_service_can_hold_key_and_human_can_sign(self):
        with self.assertRaises(PermissionError):
            ApprovalSigningBoundary(service_id="research-agent", key_id="key", key=b"k" * 32)
        with self.assertRaises(PermissionError):
            self.signing.sign(intent(), operator_role="agent")

    def test_direct_agent_unsigned_altered_and_expired_paths_fail(self):
        value = intent()
        signed = self.signed(value)
        with self.assertRaises(TradeIntentRejected):
            self.gateway.accept(signed, caller_service="research-agent", now=NOW)
        with self.assertRaises(TradeIntentRejected):
            self.gateway.accept(
                replace(signed, intent=replace(value, quantity="200")),
                caller_service="approval-service",
                now=NOW,
            )
        with self.assertRaises(TradeIntentRejected):
            self.gateway.accept(
                self.signed(replace(value, expires_at=NOW)),
                caller_service="approval-service",
                now=NOW,
            )

    def test_identical_retry_is_idempotent_but_altered_replay_fails(self):
        value = intent()
        signed = self.signed(value)
        first = self.gateway.accept(signed, caller_service="approval-service", now=NOW)
        second = self.gateway.accept(signed, caller_service="approval-service", now=NOW)
        self.assertEqual(first, second)
        altered = replace(signed, intent=replace(value, quantity="3"))
        with self.assertRaises(TradeIntentRejected):
            self.gateway.accept(altered, caller_service="approval-service", now=NOW)

    def test_risk_policy_kill_control_and_provenance_fail_closed(self):
        blocked = BrokerGatewayBoundary(
            verify=self.signing.verify,
            risk_policy=lambda _: False,
            controls=self.controls,
            audit=self.events.append,
        )
        with self.assertRaises(TradeIntentRejected):
            blocked.accept(self.signed(intent()), caller_service="approval-service", now=NOW)
        self.controls.set_state(
            operator_role="authorized-operator",
            confirmation="CONFIRM",
            reason="test",
            trade_intent_enabled=False,
        )
        with self.assertRaises(RuntimeError):
            self.gateway.accept(self.signed(intent()), caller_service="approval-service", now=NOW)
        with self.assertRaises(TradeIntentRejected):
            self.gateway.accept(
                self.signed(intent(provenance={})), caller_service="approval-service", now=NOW
            )

    def test_canonical_schema_is_versioned(self):
        schema = (ROOT / "config/trade-intent-schema.json").read_text()
        self.assertIn('"const": "1.0"', schema)
        for field in ("correlation_id", "risk_policy_version", "approval_id", "provenance"):
            self.assertIn(f'"{field}"', schema)


if __name__ == "__main__":
    unittest.main()
