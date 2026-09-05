from __future__ import annotations

import json
import unittest
from pathlib import Path

from financial_manager.alert_routing import (
    AlertDeliveryFailed,
    AlertRouter,
    OperationalAlert,
    load_routing_policy,
)
from financial_manager.observability import Metrics

ROOT = Path(__file__).resolve().parents[1]


class Channel:
    def __init__(self, name: str, failures: int = 0) -> None:
        self.name = name
        self.failures = failures
        self.calls = 0

    def send(self, alert: OperationalAlert) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("provider unavailable")
        return f"{self.name}-receipt-{alert.fingerprint}"


class AlertRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_routing_policy(ROOT / "config/alert-routing.json")
        self.metrics = Metrics()
        self.audit: list[dict[str, object]] = []
        self.email = Channel("email")
        self.sms = Channel("sms")

    def alert(self, severity: str) -> OperationalAlert:
        return OperationalAlert(
            fingerprint=f"test-{severity}",
            name="UnsafeAgentAction",
            severity=severity,
            owner="platform-operator",
            summary="Representative delivery test",
            runbook_url="docs/runbooks/operational-alerts.md",
        )

    def router(self) -> AlertRouter:
        return AlertRouter(
            policy=self.policy,
            channels={"email": self.email, "sms": self.sms},
            audit=self.audit.append,
            metrics=self.metrics,
            wait=lambda _: None,
        )

    def test_high_uses_email_only_when_delivery_succeeds(self):
        report = self.router().route(self.alert("high"))
        self.assertEqual(set(report.delivered), {"email"})
        self.assertEqual(self.email.calls, 1)
        self.assertEqual(self.sms.calls, 0)

    def test_critical_reaches_email_and_sms(self):
        report = self.router().route(self.alert("critical"))
        self.assertEqual(set(report.delivered), {"email", "sms"})
        self.assertEqual(self.email.calls, 1)
        self.assertEqual(self.sms.calls, 1)

    def test_high_email_failure_retries_then_falls_back_to_sms(self):
        self.email.failures = 3
        report = self.router().route(self.alert("high"))
        self.assertEqual(self.email.calls, 3)
        self.assertEqual(set(report.delivered), {"sms"})
        rendered = self.metrics.render()
        self.assertIn('fm_alert_delivery_failures_total{channel="email"} 1', rendered)
        self.assertNotIn("provider unavailable", json.dumps(self.audit))

    def test_total_delivery_failure_is_observable_and_raises(self):
        self.email.failures = 3
        self.sms.failures = 3
        with self.assertRaises(AlertDeliveryFailed):
            self.router().route(self.alert("high"))
        rendered = self.metrics.render()
        self.assertIn('fm_alert_delivery_failures_total{channel="email"} 1', rendered)
        self.assertIn('fm_alert_delivery_failures_total{channel="sms"} 1', rendered)

    def test_configuration_contains_no_destination_or_credential_values(self):
        routing = (ROOT / "config/alert-routing.json").read_text().lower()
        alertmanager = (ROOT / "infra/observability/alertmanager.yaml").read_text().lower()
        secrets = json.loads((ROOT / "config/secrets-policy.json").read_text())
        for prohibited in ("@", "+1", "password", "bearer "):
            self.assertNotIn(prohibited, routing + alertmanager)
        names = {item["name"] for item in secrets["secrets"]}
        self.assertTrue(
            {
                "ALERT_EMAIL_RECIPIENT",
                "ALERT_SMS_RECIPIENT",
                "ALERT_EMAIL_CREDENTIAL",
                "ALERT_SMS_ORIGINATION_NUMBER",
            }.issubset(names)
        )
        self.assertNotIn("ALERT_SMS_CREDENTIAL", names)

    def test_alertmanager_routes_high_and_critical_to_internal_router(self):
        content = (ROOT / "infra/observability/alertmanager.yaml").read_text()
        self.assertIn('severity=~"high|critical"', content)
        self.assertIn("http://alert-router:8081/alerts", content)
        self.assertIn("AlertDeliveryFailure", (ROOT / "infra/observability/alerts.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
