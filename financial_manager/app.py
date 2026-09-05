"""Financial Manager application shell and notification setup menus."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from financial_manager.notification_settings import (
    LocalAuditSink,
    NotificationSettings,
    NotificationSettingsStore,
    SettingsValidationError,
    default_settings_path,
)


class UserInterface(Protocol):
    def prompt(self, message: str) -> str: ...

    def display(self, message: str) -> None: ...


class ConsoleInterface:
    def prompt(self, message: str) -> str:
        return input(message)

    def display(self, message: str) -> None:
        print(message)


class NotificationSetupWizard:
    def __init__(self, ui: UserInterface) -> None:
        self.ui = ui

    def run(
        self, current: NotificationSettings | None, *, required: bool
    ) -> NotificationSettings | None:
        self.ui.display("Notification setup")
        self.ui.display(
            "AWS passwords and access keys are never entered here. Use AWS SSO or an AWS profile."
        )
        base = current or NotificationSettings()
        while True:
            candidate = self._collect_candidate(base)
            try:
                candidate.validate()
            except SettingsValidationError as exc:
                self.ui.display(str(exc))
                self.ui.display("Please correct the setup values.")
                continue
            self.ui.display("Review (sensitive values masked):")
            for line in candidate.masked_summary():
                self.ui.display(f"- {line}")
            if not candidate.email_enabled and not candidate.sms_enabled:
                confirmed_disabled = self._yes_no("Continue with all alerts disabled", False)
                if not confirmed_disabled:
                    return None
            if not self._yes_no("Save notification settings", True):
                if required:
                    self.ui.display("Setup is required before normal operation.")
                return None
            return candidate

    def _collect_candidate(self, base: NotificationSettings) -> NotificationSettings:
        email_enabled = self._yes_no("Enable email alerts", base.email_enabled)
        email_recipient = base.email_recipient
        if email_enabled:
            email_recipient = self._value(
                "Email recipient", base.email_recipient, secret_display=True
            )
        sms_enabled = self._yes_no("Enable SMS alerts", base.sms_enabled)
        aws_region = base.aws_region
        aws_profile = base.aws_profile
        sms_recipient = base.sms_recipient
        sms_origination = base.sms_origination_number
        sms_max_price = base.sms_max_price_usd
        if sms_enabled:
            aws_region = self._value("AWS region", base.aws_region)
            aws_profile = self._value("AWS SSO/profile name", base.aws_profile)
            sms_recipient = self._value(
                "SMS destination in E.164 format", base.sms_recipient, secret_display=True
            )
            sms_origination = self._value(
                "Registered AWS origination number",
                base.sms_origination_number,
                secret_display=True,
            )
            sms_max_price = self._value("Maximum USD per SMS", base.sms_max_price_usd)
        return replace(
            base,
            setup_complete=True,
            email_enabled=email_enabled,
            email_recipient=email_recipient if email_enabled else "",
            sms_enabled=sms_enabled,
            aws_region=aws_region,
            aws_profile=aws_profile,
            sms_recipient=sms_recipient if sms_enabled else "",
            sms_origination_number=sms_origination if sms_enabled else "",
            sms_max_price_usd=sms_max_price,
        )

    def _yes_no(self, label: str, default: bool) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            answer = self.ui.prompt(f"{label} {suffix}: ").strip().lower()
            if not answer:
                return default
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            self.ui.display("Enter yes or no.")

    def _value(self, label: str, current: str, *, secret_display: bool = False) -> str:
        hint = " [press Enter to keep current]" if current else ""
        if current and not secret_display:
            hint = f" [{current}]"
        answer = self.ui.prompt(f"{label}{hint}: ").strip()
        return answer or current


class FinancialManagerApplication:
    def __init__(
        self,
        *,
        store: NotificationSettingsStore,
        ui: UserInterface,
        actor: str,
    ) -> None:
        self.store = store
        self.ui = ui
        self.actor = actor
        self.wizard = NotificationSetupWizard(ui)

    def run(self) -> int:
        if not self.store.exists():
            self.ui.display("Welcome to Financial Manager. First-run setup is required.")
            configured = self.wizard.run(None, required=True)
            if configured is None:
                return 2
            self.store.save(configured, actor=self.actor)
            self.ui.display("Notification setup saved.")
        else:
            try:
                self.store.load()
            except SettingsValidationError as exc:
                self.ui.display(f"{exc}. Recovery setup is required.")
                configured = self.wizard.run(None, required=True)
                if configured is None:
                    return 2
                self.store.save(configured, actor=self.actor)
                self.ui.display("Notification setup recovered and saved.")
        return self._main_menu()

    def _main_menu(self) -> int:
        while True:
            self.ui.display("Main menu: 1) Continue  2) Settings  3) Exit")
            choice = self.ui.prompt("Select: ").strip()
            if choice == "1":
                self.ui.display("Financial Manager configuration is ready.")
            elif choice == "2":
                self._settings_menu()
            elif choice == "3":
                return 0
            else:
                self.ui.display("Select 1, 2, or 3.")

    def _settings_menu(self) -> None:
        while True:
            self.ui.display("Settings: 1) Notifications  2) Back")
            choice = self.ui.prompt("Select: ").strip()
            if choice == "1":
                current = self.store.load()
                configured = self.wizard.run(current, required=False)
                if configured is not None:
                    self.store.save(configured, actor=self.actor)
                    self.ui.display("Notification settings updated.")
            elif choice == "2":
                return
            else:
                self.ui.display("Select 1 or 2.")


def main(
    argv: list[str] | None = None,
    *,
    audit: Callable[[dict[str, object]], None] | None = None,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", type=Path, default=default_settings_path())
    parser.add_argument("--actor", default="local-operator")
    args = parser.parse_args(argv)
    audit_sink = audit or LocalAuditSink(args.settings.with_name("settings-audit.jsonl"))
    application = FinancialManagerApplication(
        store=NotificationSettingsStore(args.settings, audit_sink),
        ui=ConsoleInterface(),
        actor=args.actor,
    )
    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
