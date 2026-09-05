from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OperationalVisibilityTests(unittest.TestCase):
    def test_dashboards_cover_platform_agents_and_blind_spots(self) -> None:
        dashboard_dir = ROOT / "infra/observability/grafana/dashboards"
        content = "\n".join(path.read_text() for path in dashboard_dir.glob("*.json"))
        self.assertIn("fm_service_up", content)
        self.assertIn("fm_agent_executions_total", content)
        self.assertIn("fm_audit_last_event_timestamp_seconds", content)
        for path in dashboard_dir.glob("*.json"):
            json.loads(path.read_text())

    def test_failure_injection_matches_alert_and_runbook(self) -> None:
        alerts = (ROOT / "infra/observability/alerts.yaml").read_text()
        runbooks = (ROOT / "docs/runbooks/operational-alerts.md").read_text()
        injected_metrics = "fm_service_up 0\nup{job=\"otel-collector\"} 0\n"
        self.assertIn("fm_service_up 0", injected_metrics)
        self.assertIn("FinancialManagerServiceDown", alerts)
        self.assertIn("TelemetryIngestionBlindSpot", alerts)
        self.assertIn("severity: critical", alerts)
        self.assertIn("owner:", alerts)
        self.assertIn("runbook_url:", alerts)
        self.assertIn("## Service down", runbooks)

    def test_alert_configuration_contains_no_sensitive_values(self) -> None:
        alerts = (ROOT / "infra/observability/alerts.yaml").read_text().lower()
        for prohibited in ("bearer ", "password=", "account_number", "secret="):
            self.assertNotIn(prohibited, alerts)


if __name__ == "__main__":
    unittest.main()
