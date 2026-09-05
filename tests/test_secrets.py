from __future__ import annotations

import json
import unittest
from pathlib import Path

from financial_manager.audit import redact
from financial_manager.secrets import (
    EnvironmentSecretStore,
    SecretAccessError,
    SecretUnavailableError,
    load_policy,
)

ROOT = Path(__file__).resolve().parents[1]
POLICIES = load_policy(ROOT / "config/secrets-policy.json")


class SecretManagementTests(unittest.TestCase):
    def store(self, service: str, environment: str, values: dict[str, str]):
        events: list[dict[str, str]] = []
        return EnvironmentSecretStore(
            service_id=service,
            environment=environment,
            policies=POLICIES,
            audit=events.append,
            environ=values,
        ), events

    def test_authorized_runtime_injection_is_opaque_and_audited(self):
        store, events = self.store(
            "market-data-gateway", "dev", {"FM_DEV_MARKET_DATA_API_KEY": "value-123"}
        )
        value = store.get("MARKET_DATA_API_KEY")
        self.assertEqual(value.reveal(), "value-123")
        self.assertEqual(str(value), "[REDACTED]")
        self.assertNotIn("value-123", repr(value))
        self.assertEqual(events[-1]["result"], "allowed")
        self.assertNotIn("value-123", json.dumps(events))

    def test_unauthorized_service_and_environment_fail_closed(self):
        store, events = self.store(
            "research-agent", "prod", {"FM_PROD_BROKER_CREDENTIAL": "broker-secret"}
        )
        with self.assertRaises(SecretAccessError):
            store.get("BROKER_CREDENTIAL")
        self.assertEqual(events[-1]["reason"], "service-not-authorized")

        nonprod, _ = self.store(
            "broker-gateway", "test", {"FM_TEST_BROKER_CREDENTIAL": "wrong-env"}
        )
        with self.assertRaises(SecretAccessError):
            nonprod.get("BROKER_CREDENTIAL")

    def test_missing_and_revoked_secrets_fail_closed(self):
        store, events = self.store("news-gateway", "dev", {})
        with self.assertRaises(SecretUnavailableError):
            store.get("NEWS_API_KEY")
        self.assertEqual(events[-1]["reason"], "not-injected")

        live, _ = self.store(
            "broker-gateway", "prod", {"FM_PROD_BROKER_CREDENTIAL": "broker-secret"}
        )
        live.revoke("BROKER_CREDENTIAL", operator_role="authorized-operator")
        with self.assertRaises(SecretAccessError):
            live.get("BROKER_CREDENTIAL")

    def test_agents_are_never_allowlisted_for_live_execution_secrets(self):
        for policy in POLICIES.values():
            if policy.live_execution:
                self.assertFalse(
                    any("agent" in service or "llm" in service for service in policy.authorized_services)
                )

    def test_recursive_redaction_covers_secret_key_variants(self):
        value = redact(
            {
                "api_key": "one",
                "private-key": "two",
                "nested": {"connection_string": "three", "safe": "visible"},
            }
        )
        self.assertEqual(value["api_key"], "[REDACTED]")
        self.assertEqual(value["private-key"], "[REDACTED]")
        self.assertEqual(value["nested"]["connection_string"], "[REDACTED]")
        self.assertEqual(value["nested"]["safe"], "visible")


if __name__ == "__main__":
    unittest.main()
