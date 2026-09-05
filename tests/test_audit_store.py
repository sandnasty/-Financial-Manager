from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from financial_manager.audit import AuditEvent, PostgresAuditStore

ROOT = Path(__file__).resolve().parents[1]


class Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.rows: list[tuple[object, ...]] = []

    def execute(self, query: str, parameters: tuple[object, ...] = ()) -> Cursor:
        self.calls.append((query, parameters))
        if "append_event" in query:
            return Cursor([("11111111-1111-1111-1111-111111111111",)])
        return Cursor(self.rows)


def event(action: str = "trade.recommended") -> AuditEvent:
    return AuditEvent.create(
        event_id=UUID("11111111-1111-1111-1111-111111111111"),
        occurred_at=datetime(2026, 9, 5, tzinfo=UTC),
        actor_id="research-agent-1",
        actor_type="agent",
        action=action,
        target_type="TradeIntent",
        target_id="TI-42",
        correlation_id="trade-flow-42",
        trace_id="trace-42",
        result="success",
        source_service="decision-service",
        source_version="0.1.0+sha.abc",
        environment="TEST",
        immutable_refs={"policy_version": "risk-v1"},
        details={"authorization": "Bearer secret", "score": 0.82},
    )


class AuditStoreTests(unittest.TestCase):
    def test_event_is_redacted_before_append(self) -> None:
        connection = Connection()
        stored_id = PostgresAuditStore(connection).append(event())
        self.assertEqual(stored_id, "11111111-1111-1111-1111-111111111111")
        payload = json.loads(connection.calls[0][1][0])
        self.assertEqual(payload["details"]["authorization"], "[REDACTED]")
        self.assertEqual(payload["details"]["score"], 0.82)
        self.assertRegex(str(connection.calls[0][1][1]), r"^[0-9a-f]{64}$")

    def test_reconstruct_orders_one_correlated_trade_sequence(self) -> None:
        connection = Connection()
        connection.rows = [
            ({"action": "trade.recommended"},),
            ({"action": "trade.approved"},),
            ({"action": "brokerage.handoff"},),
        ]
        result = PostgresAuditStore(connection).reconstruct("trade-flow-42")
        self.assertEqual(
            [item["action"] for item in result],
            ["trade.recommended", "trade.approved", "brokerage.handoff"],
        )
        self.assertIn("ORDER BY sequence_number", connection.calls[0][0])

    def test_database_contract_denies_mutation_and_chains_records(self) -> None:
        sql = (ROOT / "infra/postgres/audit.sql").read_text(encoding="utf-8")
        self.assertIn("BEFORE UPDATE OR DELETE", sql)
        self.assertIn("REVOKE INSERT, UPDATE, DELETE, TRUNCATE", sql)
        self.assertIn("prior_record_sha256", sql)
        self.assertIn("pg_advisory_xact_lock", sql)


if __name__ == "__main__":
    unittest.main()
