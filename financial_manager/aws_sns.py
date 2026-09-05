"""Amazon SNS SMS provider adapter for operational alerts."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from financial_manager.alert_routing import OperationalAlert

_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
_ORIGINATION_NUMBER = re.compile(r"^\+?[0-9]{5,14}$")
_SMS_MAX_CHARACTERS = 140


class SNSPublishClient(Protocol):
    """Narrow protocol implemented by the Boto3 SNS client."""

    def publish(self, **kwargs: Any) -> Mapping[str, Any]: ...


SNSClientFactory = Callable[..., SNSPublishClient]


class SNSConfigurationError(ValueError):
    """Raised when required SNS runtime configuration is missing or unsafe."""


class SNSDeliveryError(RuntimeError):
    """Raised when SNS accepts no auditable delivery receipt."""


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise SNSConfigurationError(f"{name} is required")
    return value


def _render_message(alert: OperationalAlert) -> str:
    raw = (
        f"Financial Manager {alert.severity.upper()}: {alert.name}. "
        f"{alert.summary} Runbook: {alert.runbook_url}"
    )
    ascii_message = raw.encode("ascii", errors="replace").decode("ascii")
    if len(ascii_message) <= _SMS_MAX_CHARACTERS:
        return ascii_message
    return f"{ascii_message[: _SMS_MAX_CHARACTERS - 3].rstrip()}..."


class AWSSNSSMSChannel:
    """Send one-part transactional SMS alerts through Amazon SNS."""

    def __init__(
        self,
        *,
        client: SNSPublishClient,
        phone_number: str,
        origination_number: str | None,
        max_price_usd: str = "0.05",
    ) -> None:
        if not _E164.fullmatch(phone_number):
            raise SNSConfigurationError("ALERT_SMS_RECIPIENT must use E.164 format")
        if origination_number and not _ORIGINATION_NUMBER.fullmatch(origination_number):
            raise SNSConfigurationError(
                "ALERT_SMS_ORIGINATION_NUMBER must contain 5-14 digits and an optional +"
            )
        try:
            max_price = Decimal(max_price_usd)
        except InvalidOperation as exc:
            raise SNSConfigurationError("ALERT_SMS_MAX_PRICE_USD must be numeric") from exc
        if not max_price.is_finite() or max_price <= 0 or max_price > Decimal("1.00"):
            raise SNSConfigurationError(
                "ALERT_SMS_MAX_PRICE_USD must be greater than 0 and no more than 1.00"
            )
        self.client = client
        self.phone_number = phone_number
        self.origination_number = origination_number
        self.max_price_usd = format(max_price, "f")

    @classmethod
    def from_environment(
        cls,
        *,
        environ: Mapping[str, str] = os.environ,
        client_factory: SNSClientFactory | None = None,
    ) -> AWSSNSSMSChannel:
        """Build the adapter from protected runtime configuration and the AWS IAM chain."""

        region = _required(environ, "AWS_REGION")
        phone_number = _required(environ, "ALERT_SMS_RECIPIENT")
        origination_number = _required(environ, "ALERT_SMS_ORIGINATION_NUMBER")
        max_price = environ.get("ALERT_SMS_MAX_PRICE_USD", "0.05").strip()
        if client_factory is None:
            from boto3 import client as boto3_client

            client_factory = boto3_client
        client = client_factory("sns", region_name=region)
        return cls(
            client=client,
            phone_number=phone_number,
            origination_number=origination_number,
            max_price_usd=max_price,
        )

    def send(self, alert: OperationalAlert) -> str:
        attributes: dict[str, dict[str, str]] = {
            "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"},
            "AWS.SNS.SMS.MaxPrice": {
                "DataType": "Number",
                "StringValue": self.max_price_usd,
            },
        }
        if self.origination_number:
            attributes["AWS.MM.SMS.OriginationNumber"] = {
                "DataType": "String",
                "StringValue": self.origination_number,
            }
        response = self.client.publish(
            PhoneNumber=self.phone_number,
            Message=_render_message(alert),
            MessageAttributes=attributes,
        )
        message_id = response.get("MessageId")
        if not isinstance(message_id, str) or not message_id:
            raise SNSDeliveryError("Amazon SNS returned no MessageId")
        return message_id
