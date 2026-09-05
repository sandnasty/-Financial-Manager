from __future__ import annotations

import unittest
from pathlib import Path

from financial_manager.controls import ActionDisabled, AuthorizationError, OperationalControls

ROOT = Path(__file__).resolve().parents[1]


class OperationalControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[dict[str, str]] = []
        self.controls = OperationalControls(self.events.append)

    def test_agent_cannot_change_controls(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.controls.set_state(operator_role="agent", confirmation="CONFIRM",
                                    reason="test", global_enabled=False)

    def test_disable_blocks_trade_intent_and_is_audited(self) -> None:
        self.controls.set_state(operator_role="authorized-operator",
                                confirmation="CONFIRM", reason="unsafe",
                                trade_intent_enabled=False)
        with self.assertRaises(ActionDisabled):
            self.controls.require_action("trade-intent.submit", "research")
        self.assertEqual(self.events[0]["action"], "operational-control.changed")

    def test_restore_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.controls.set_state(operator_role="authorized-operator",
                                    confirmation="", reason="restore",
                                    global_enabled=True)

    def test_rollback_is_digest_signed_and_prod_approved(self) -> None:
        text = (ROOT / ".github/workflows/rollback.yml").read_text()
        self.assertIn("environment:\n      name: PROD", text)
        self.assertIn("cosign verify", text)
        self.assertIn("^sha256:[0-9a-f]{64}$", text)
        self.assertIn("retention-days: 365", text)


if __name__ == "__main__":
    unittest.main()
