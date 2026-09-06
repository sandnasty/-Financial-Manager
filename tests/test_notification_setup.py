from __future__ import annotations

import json
import os
import pathlib
import stat
import tempfile
import unittest
from collections.abc import Iterable

from financial_manager.app import FinancialManagerApplication, NotificationSetupWizard
from financial_manager.notification_settings import (
    LocalAuditSink,
    NotificationSettings,
    NotificationSettingsStore,
    SettingsValidationError,
    default_settings_path,
)


class ScriptedInterface:
    def __init__(self, answers: Iterable[str]) -> None:
        self.answers = iter(answers)
        self.messages: list[str] = []

    def prompt(self, message: str) -> str:
        self.messages.append(message)
        return next(self.answers)

    def display(self, message: str) -> None:
        self.messages.append(message)


class NotificationSettingsTest(unittest.TestCase):
    def test_default_path_is_outside_checkout(self) -> None:
        path = default_settings_path(environ={}, home=pathlib.Path("/home/operator"))
        self.assertEqual(
            path,
            pathlib.Path("/home/operator/.config/financial-manager/settings.json"),
        )

    def test_store_is_owner_only_and_audit_contains_no_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            settings_path = root / "config" / "settings.json"
            audit_path = root / "config" / "settings-audit.jsonl"
            store = NotificationSettingsStore(settings_path, LocalAuditSink(audit_path))
            settings = NotificationSettings(
                setup_complete=True,
                email_enabled=True,
                email_recipient="owner@example.com",
                sms_enabled=True,
                sms_topic_arn="arn:aws:sns:us-east-1:111122223333:alerts",
                sms_recipient="+12025550123",
                sms_origination_number="+18005550123",
            )

            store.save(settings, actor="local-operator")

            self.assertEqual(store.load(), settings)
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(settings_path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(audit_path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(settings_path.parent.stat().st_mode), 0o700)
            audit_text = audit_path.read_text(encoding="utf-8")
            self.assertNotIn("owner@example.com", audit_text)
            self.assertNotIn("+12025550123", audit_text)
            event = json.loads(audit_text)
            self.assertEqual(event["action"], "notification-settings.changed")
            self.assertIn("email_recipient", event["changed_fields"])

    def test_invalid_sms_configuration_fails_closed(self) -> None:
        settings = NotificationSettings(
            setup_complete=True,
            sms_enabled=True,
            sms_topic_arn="arn:aws:sns:us-east-1:111122223333:alerts",
            sms_recipient="2025550123",
            sms_origination_number="not-a-number",
        )
        with self.assertRaises(SettingsValidationError):
            settings.validate()

    def test_runtime_environment_uses_destinations_and_profile_not_credentials(self) -> None:
        settings = NotificationSettings(
            setup_complete=True,
            email_enabled=True,
            email_recipient="owner@example.com",
            sms_enabled=True,
            aws_profile="financial-manager",
            sms_topic_arn="arn:aws:sns:us-east-1:111122223333:alerts",
            sms_recipient="+12025550123",
            sms_origination_number="+18005550123",
        )
        environment = settings.runtime_environment()
        self.assertEqual(environment["ALERT_EMAIL_RECIPIENT"], "owner@example.com")
        self.assertEqual(environment["AWS_PROFILE"], "financial-manager")
        self.assertEqual(
            environment["ALERT_SMS_TOPIC_ARN"],
            "arn:aws:sns:us-east-1:111122223333:alerts",
        )
        self.assertFalse(any("KEY" in name or "TOKEN" in name for name in environment))


class NotificationApplicationTest(unittest.TestCase):
    def _application(
        self, directory: str, answers: Iterable[str]
    ) -> tuple[FinancialManagerApplication, NotificationSettingsStore, ScriptedInterface]:
        root = pathlib.Path(directory)
        events: list[dict[str, object]] = []
        store = NotificationSettingsStore(root / "settings.json", events.append)
        ui = ScriptedInterface(answers)
        app = FinancialManagerApplication(store=store, ui=ui, actor="test-operator")
        return app, store, ui

    def test_first_run_collects_both_channels_and_masks_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app, store, ui = self._application(
                directory,
                [
                    "yes",
                    "owner@example.com",
                    "yes",
                    "",
                    "financial-manager",
                    "arn:aws:sns:us-east-1:111122223333:alerts",
                    "+12025550123",
                    "+18005550123",
                    "",
                    "yes",
                    "3",
                ],
            )

            self.assertEqual(app.run(), 0)
            settings = store.load()
            self.assertTrue(settings.email_enabled)
            self.assertTrue(settings.sms_enabled)
            displayed = "\n".join(ui.messages)
            self.assertNotIn("owner@example.com", displayed)
            self.assertNotIn("+12025550123", displayed)
            self.assertIn("o****@example.com", displayed)
            self.assertIn("*******0123", displayed)

    def test_settings_menu_can_change_setup_later(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app, store, _ = self._application(
                directory,
                [
                    "2",
                    "1",
                    "",
                    "",
                    "yes",
                    "",
                    "",
                    "arn:aws:sns:us-east-1:111122223333:alerts",
                    "+12025550123",
                    "+18005550123",
                    "",
                    "yes",
                    "2",
                    "3",
                ],
            )
            store.save(
                NotificationSettings(
                    setup_complete=True,
                    email_enabled=True,
                    email_recipient="owner@example.com",
                ),
                actor="test-operator",
            )

            self.assertEqual(app.run(), 0)
            updated = store.load()
            self.assertTrue(updated.email_enabled)
            self.assertTrue(updated.sms_enabled)

    def test_canceling_required_setup_prevents_normal_operation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app, store, _ = self._application(directory, ["no", "no", "yes", "no"])

            self.assertEqual(app.run(), 2)
            self.assertFalse(store.exists())

    def test_invalid_file_starts_recovery_setup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app, store, ui = self._application(
                directory, ["no", "no", "yes", "yes", "3"]
            )
            store.path.write_text("not json", encoding="utf-8")

            self.assertEqual(app.run(), 0)
            self.assertTrue(store.load().setup_complete)
            self.assertIn("Recovery setup is required", "\n".join(ui.messages))

    def test_validation_error_reprompts_without_saving_bad_values(self) -> None:
        ui = ScriptedInterface(
            [
                "yes",
                "invalid",
                "no",
                "yes",
                "owner@example.com",
                "no",
                "yes",
            ]
        )
        configured = NotificationSetupWizard(ui).run(None, required=True)

        self.assertIsNotNone(configured)
        assert configured is not None
        self.assertEqual(configured.email_recipient, "owner@example.com")
        self.assertIn("Please correct the setup values.", ui.messages)


if __name__ == "__main__":
    unittest.main()
