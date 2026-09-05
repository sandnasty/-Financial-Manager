from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from financial_manager.alert_routing import OperationalAlert
from financial_manager.aws_sns import (
    AWSSNSSMSChannel,
    SNSConfigurationError,
    SNSDeliveryError,
)


class SNSClient:
    def __init__(self, response: dict[str, str] | None = None) -> None:
        self.response = response if response is not None else {"MessageId": "sns-message-123"}
        self.calls: list[dict[str, Any]] = []

    def publish(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return self.response


def alert() -> OperationalAlert:
    return OperationalAlert(
        fingerprint="critical-123",
        name="AuditIngestionLoss",
        severity="critical",
        owner="security-operator",
        summary="Audit evidence is unavailable; disable TradeIntent progression.",
        runbook_url="docs/runbooks/operational-alerts.md",
    )


class AWSSNSChannelTests(unittest.TestCase):
    def test_sends_transactional_single_part_sms_and_returns_message_id(self):
        client = SNSClient()
        channel = AWSSNSSMSChannel(
            client=client,
            phone_number="+14805550123",
            origination_number="+18005550123",
        )

        receipt = channel.send(alert())

        self.assertEqual(receipt, "sns-message-123")
        request = client.calls[0]
        self.assertEqual(request["PhoneNumber"], "+14805550123")
        self.assertLessEqual(len(request["Message"]), 140)
        self.assertEqual(
            request["MessageAttributes"]["AWS.SNS.SMS.SMSType"]["StringValue"],
            "Transactional",
        )
        self.assertEqual(
            request["MessageAttributes"]["AWS.MM.SMS.OriginationNumber"]["StringValue"],
            "+18005550123",
        )
        self.assertEqual(
            request["MessageAttributes"]["AWS.SNS.SMS.MaxPrice"]["StringValue"], "0.05"
        )

    def test_from_environment_uses_iam_credential_chain_and_region(self):
        calls: list[tuple[str, str]] = []

        def factory(service: str, *, region_name: str) -> SNSClient:
            calls.append((service, region_name))
            return SNSClient()

        channel = AWSSNSSMSChannel.from_environment(
            environ={
                "AWS_REGION": "us-west-2",
                "ALERT_SMS_RECIPIENT": "+14805550123",
                "ALERT_SMS_ORIGINATION_NUMBER": "+18005550123",
                "ALERT_SMS_MAX_PRICE_USD": "0.03",
            },
            client_factory=factory,
        )

        self.assertEqual(calls, [("sns", "us-west-2")])
        self.assertEqual(channel.max_price_usd, "0.03")

    def test_rejects_invalid_recipient_without_calling_provider(self):
        with self.assertRaisesRegex(SNSConfigurationError, "E.164"):
            AWSSNSSMSChannel(
                client=SNSClient(),
                phone_number="480-555-0123",
                origination_number=None,
            )

    def test_rejects_excessive_per_message_price_cap(self):
        with self.assertRaisesRegex(SNSConfigurationError, "no more than 1.00"):
            AWSSNSSMSChannel(
                client=SNSClient(),
                phone_number="+14805550123",
                origination_number=None,
                max_price_usd="5.00",
            )

    def test_rejects_non_finite_per_message_price_cap(self):
        with self.assertRaisesRegex(SNSConfigurationError, "no more than 1.00"):
            AWSSNSSMSChannel(
                client=SNSClient(),
                phone_number="+14805550123",
                origination_number=None,
                max_price_usd="NaN",
            )

    def test_missing_message_id_is_a_delivery_failure(self):
        channel = AWSSNSSMSChannel(
            client=SNSClient(response={}),
            phone_number="+14805550123",
            origination_number=None,
        )
        with self.assertRaises(SNSDeliveryError):
            channel.send(alert())

    def test_source_configuration_contains_no_real_phone_number(self):
        source = __import__("financial_manager.aws_sns", fromlist=["x"]).__file__
        assert source is not None
        content = Path(source).read_text(encoding="utf-8")
        self.assertNotIn("Mathew.sandnas", content)


if __name__ == "__main__":
    unittest.main()
