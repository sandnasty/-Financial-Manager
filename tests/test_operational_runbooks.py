from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RunbookTests(unittest.TestCase):
    def test_required_scenarios_roles_and_closure_are_documented(self) -> None:
        text = (ROOT / "docs/runbooks/index.md").read_text()
        for phrase in ("Service outage", "Agent/tool failure", "Audit loss",
                       "Telemetry loss", "Critical vulnerability",
                       "Credential compromise", "Bad deployment", "Unsafe agent"):
            self.assertIn(phrase, text)
        self.assertIn("Immediate action", text)
        self.assertIn("Validate and close", text)
        self.assertIn("immutable audit event", text)

    def test_retention_and_evidence_integrity_are_defined(self) -> None:
        text = (ROOT / "docs/operations/retention-and-evidence.md").read_text()
        self.assertIn("365 days", text)
        self.assertIn("90 days", text)
        self.assertIn("100,000 audit events/day", text)
        self.assertIn("correlation and trace IDs", text)
        self.assertIn("SHA-256", text)
        self.assertIn("redaction", text)

    def test_tabletop_uses_controls_and_records_gap(self) -> None:
        text = (ROOT / "docs/operations/tabletop-unsafe-agent.md").read_text()
        self.assertIn("TradeIntent", text)
        self.assertIn("Controlled Rollback", text)
        self.assertIn("explicitly approves", text)
        self.assertIn("Gap:", text)


if __name__ == "__main__":
    unittest.main()
