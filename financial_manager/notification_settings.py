"""Secure local notification settings for the application setup flow."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

AuditSink = Callable[[dict[str, Any]], None]

_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
_AWS_REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+$")
_AWS_PROFILE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SNS_TOPIC_ARN = re.compile(
    r"^arn:(?:aws|aws-us-gov|aws-cn):sns:(?P<region>[a-z0-9-]+):"
    r"(?P<account>[0-9]{12}):(?P<topic>[A-Za-z0-9_-]{1,256})$"
)


class SettingsValidationError(ValueError):
    """Raised when notification settings are incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class NotificationSettings:
    """Non-credential configuration entered through Settings > Notifications."""

    schema_version: int = 1
    setup_complete: bool = False
    email_enabled: bool = False
    email_recipient: str = ""
    sms_enabled: bool = False
    aws_region: str = "us-east-1"
    aws_profile: str = "default"
    sms_topic_arn: str = ""
    sms_recipient: str = ""
    sms_origination_number: str = ""
    sms_max_price_usd: str = "0.05"

    def validate(self) -> None:
        errors: list[str] = []
        if self.schema_version != 1:
            errors.append("schema_version")
        if not self.setup_complete:
            errors.append("setup_complete")
        if self.email_enabled and not _valid_email(self.email_recipient):
            errors.append("email_recipient")
        if self.sms_enabled:
            if not _AWS_REGION.fullmatch(self.aws_region):
                errors.append("aws_region")
            if not _AWS_PROFILE.fullmatch(self.aws_profile):
                errors.append("aws_profile")
            topic_match = _SNS_TOPIC_ARN.fullmatch(self.sms_topic_arn)
            if topic_match is None or topic_match.group("region") != self.aws_region:
                errors.append("sms_topic_arn")
            if not _E164.fullmatch(self.sms_recipient):
                errors.append("sms_recipient")
            if not _E164.fullmatch(self.sms_origination_number):
                errors.append("sms_origination_number")
            if not _valid_price(self.sms_max_price_usd):
                errors.append("sms_max_price_usd")
        if errors:
            joined = ", ".join(sorted(set(errors)))
            raise SettingsValidationError(f"invalid notification settings fields: {joined}")

    def runtime_environment(self) -> dict[str, str]:
        self.validate()
        environment: dict[str, str] = {}
        if self.email_enabled:
            environment["ALERT_EMAIL_RECIPIENT"] = self.email_recipient
        if self.sms_enabled:
            environment.update(
                {
                    "AWS_REGION": self.aws_region,
                    "AWS_PROFILE": self.aws_profile,
                    "ALERT_SMS_TOPIC_ARN": self.sms_topic_arn,
                    "ALERT_SMS_RECIPIENT": self.sms_recipient,
                    "ALERT_SMS_ORIGINATION_NUMBER": self.sms_origination_number,
                    "ALERT_SMS_MAX_PRICE_USD": self.sms_max_price_usd,
                }
            )
        return environment

    def masked_summary(self) -> tuple[str, ...]:
        email = _mask_email(self.email_recipient) if self.email_enabled else "disabled"
        sms = _mask_phone(self.sms_recipient) if self.sms_enabled else "disabled"
        origin = _mask_phone(self.sms_origination_number) if self.sms_enabled else "disabled"
        topic = _mask_topic_arn(self.sms_topic_arn) if self.sms_enabled else "disabled"
        return (
            f"Email: {email}",
            f"SMS destination: {sms}",
            f"SMS origination: {origin}",
            f"SNS topic: {topic}",
            f"AWS region: {self.aws_region if self.sms_enabled else 'not used'}",
            f"AWS profile: {self.aws_profile if self.sms_enabled else 'not used'}",
            f"SMS price cap: {self.sms_max_price_usd if self.sms_enabled else 'not used'}",
        )


def default_settings_path(
    *, environ: Mapping[str, str] = os.environ, home: Path | None = None
) -> Path:
    if environ.get("APPDATA"):
        return Path(environ["APPDATA"]) / "Financial Manager" / "settings.json"
    if environ.get("XDG_CONFIG_HOME"):
        return Path(environ["XDG_CONFIG_HOME"]) / "financial-manager" / "settings.json"
    resolved_home = home if home is not None else Path.home()
    return resolved_home / ".config" / "financial-manager" / "settings.json"


class NotificationSettingsStore:
    def __init__(self, path: Path, audit: AuditSink) -> None:
        self.path = path
        self.audit = audit

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> NotificationSettings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            allowed = {item.name for item in fields(NotificationSettings)}
            if set(raw) - allowed:
                raise SettingsValidationError("settings contain unsupported fields")
            settings = NotificationSettings(**raw)
            settings.validate()
            return settings
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise SettingsValidationError("notification settings cannot be loaded") from exc

    def save(self, settings: NotificationSettings, *, actor: str) -> None:
        settings.validate()
        try:
            previous = self.load() if self.exists() else None
        except SettingsValidationError:
            previous = None
        changed_fields = _changed_fields(previous, settings)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        payload = json.dumps(asdict(settings), indent=2, sort_keys=True) + "\n"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=".settings-",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                os.chmod(temporary_path, 0o600)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
        self.audit(
            {
                "action": "notification-settings.changed",
                "actor": actor,
                "changed_fields": changed_fields,
                "result": "success",
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )


class LocalAuditSink:
    """Owner-readable local trace used before the platform audit service is available."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __call__(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.path, flags, 0o600)
        try:
            os.chmod(self.path, 0o600)
            payload = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
            os.write(descriptor, payload.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _changed_fields(
    previous: NotificationSettings | None, current: NotificationSettings
) -> list[str]:
    current_values = asdict(current)
    if previous is None:
        return sorted(current_values)
    previous_values = asdict(previous)
    return sorted(key for key, value in current_values.items() if previous_values[key] != value)


def _valid_email(value: str) -> bool:
    local, separator, domain = value.strip().partition("@")
    return bool(local and separator and "." in domain and " " not in value)


def _valid_price(value: str) -> bool:
    try:
        price = Decimal(value)
    except InvalidOperation:
        return False
    return price.is_finite() and Decimal("0") < price <= Decimal("1.00")


def _mask_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "not configured"
    visible = local[:1]
    return f"{visible}{'*' * max(3, len(local) - 1)}@{domain}"


def _mask_phone(value: str) -> str:
    if len(value) < 5:
        return "not configured"
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def _mask_topic_arn(value: str) -> str:
    match = _SNS_TOPIC_ARN.fullmatch(value)
    if match is None:
        return "not configured"
    account = match.group("account")
    return value.replace(account, f"{'*' * 8}{account[-4:]}", 1)
