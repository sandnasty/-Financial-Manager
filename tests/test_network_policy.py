from __future__ import annotations

import json
import unittest
from pathlib import Path

from financial_manager.network_policy import (
    NetworkAccessDenied,
    NetworkPolicy,
    ServiceNetworkPolicy,
    load_network_policy,
)

ROOT = Path(__file__).resolve().parents[1]


class NetworkPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[dict[str, str]] = []
        self.policies = load_network_policy(ROOT / "config/network-policy.json")
        self.policy = NetworkPolicy(self.policies, self.events.append)

    def test_policy_is_default_deny_and_agents_have_no_egress(self):
        raw = json.loads((ROOT / "config/network-policy.json").read_text())
        self.assertEqual(raw["default"], "deny")
        self.assertEqual(self.policies["research-agent"].egress_hosts, frozenset())
        with self.assertRaises(NetworkAccessDenied):
            self.policy.authorize_egress("research-agent", "https://broker.example")

    def test_required_and_prohibited_east_west_paths(self):
        self.policy.authorize_service("research-agent", "market-data-gateway")
        self.policy.authorize_service("approval-service", "broker-gateway")
        with self.assertRaises(NetworkAccessDenied):
            self.policy.authorize_service("research-agent", "broker-gateway")
        self.assertEqual(self.events[-1]["result"], "denied")

    def test_alert_router_has_only_regional_sns_egress(self):
        alert_router = self.policies["alert-router"]
        self.assertEqual(alert_router.east_west, frozenset())
        self.assertEqual(alert_router.egress_hosts, frozenset({"sns.us-west-2.amazonaws.com"}))
        self.policy.authorize_egress(
            "alert-router", "https://sns.us-west-2.amazonaws.com/"
        )
        with self.assertRaises(NetworkAccessDenied):
            self.policy.authorize_egress("alert-router", "https://sns.us-east-1.amazonaws.com/")

    def test_egress_requires_exact_https_host_and_audits_result(self):
        policies = dict(self.policies)
        policies["market-data-gateway"] = ServiceNetworkPolicy(
            east_west=policies["market-data-gateway"].east_west,
            egress_hosts=frozenset({"data.provider.example"}),
        )
        policy = NetworkPolicy(policies, self.events.append)
        self.assertEqual(
            policy.authorize_egress("market-data-gateway", "https://data.provider.example/path"),
            "data.provider.example",
        )
        for url in (
            "http://data.provider.example",
            "https://other.example",
            "https://data.provider.example:8443",
            "https://127.0.0.1",
            "https://user:pass@data.provider.example",
        ):
            with self.assertRaises(NetworkAccessDenied):
                policy.authorize_egress("market-data-gateway", url)
        self.assertTrue(all("occurred_at" in event for event in self.events))

    def test_compose_isolates_agent_market_and_broker_networks(self):
        compose = (ROOT / "compose.yaml").read_text()
        self.assertIn("fm_agent:", compose)
        self.assertIn("fm_broker_control:", compose)
        self.assertIn("fm_market_egress:", compose)
        self.assertIn("fm_broker_egress:", compose)
        research = compose.split("  research-agent:", 1)[1].split("  market-data-gateway:", 1)[0]
        broker = compose.split("  broker-gateway:", 1)[1].split("\nnetworks:", 1)[0]
        self.assertIn("networks: [fm_agent]", research)
        self.assertNotIn("egress", research)
        self.assertIn("fm_broker_egress", broker)
        self.assertNotIn("fm_agent", broker)


if __name__ == "__main__":
    unittest.main()
