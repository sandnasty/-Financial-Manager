import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from tools.security_gate import evaluate, normalized_trivy, validate_exceptions


class SecurityGateTests(unittest.TestCase):
    def test_unexcepted_high_finding_blocks(self) -> None:
        findings = [
            {
                "scanner": "trivy-source",
                "finding_id": "CVE-2099-0001",
                "severity": "HIGH",
                "component": "example",
                "title": "demo",
                "remediation": "upgrade",
                "location": "lockfile",
            }
        ]
        blocked, excepted = evaluate(findings, [])
        self.assertEqual(len(blocked), 1)
        self.assertEqual(excepted, [])

    def test_approved_current_exception_suppresses_matching_finding(self) -> None:
        today = date.today()
        registry = {
            "schema_version": 1,
            "exceptions": [
                {
                    "scanner": "trivy-source",
                    "finding_id": "CVE-2099-0001",
                    "component": "example",
                    "owner": "security-owner",
                    "rationale": "temporary upstream constraint",
                    "approved_by": "release-owner",
                    "review_on": (today + timedelta(days=7)).isoformat(),
                    "expires_on": (today + timedelta(days=14)).isoformat(),
                }
            ],
        }
        exceptions = validate_exceptions(registry)
        findings = [
            {
                "scanner": "trivy-source",
                "finding_id": "CVE-2099-0001",
                "severity": "CRITICAL",
                "component": "example",
                "title": "demo",
                "remediation": "upgrade",
                "location": "lockfile",
            }
        ]
        blocked, excepted = evaluate(findings, exceptions)
        self.assertEqual(blocked, [])
        self.assertEqual(len(excepted), 1)

    def test_exception_past_review_date_is_rejected(self) -> None:
        today = date.today()
        registry = {
            "schema_version": 1,
            "exceptions": [
                {
                    "scanner": "trivy-source",
                    "finding_id": "CVE-2099-0001",
                    "owner": "security-owner",
                    "rationale": "temporary upstream constraint",
                    "approved_by": "release-owner",
                    "review_on": (today - timedelta(days=1)).isoformat(),
                    "expires_on": (today + timedelta(days=14)).isoformat(),
                }
            ],
        }
        with self.assertRaises(ValueError):
            validate_exceptions(registry)

    def test_trivy_normalization_preserves_remediation_path(self) -> None:
        report = {
            "Results": [
                {
                    "Target": "pylock.toml",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2099-0002",
                            "PkgName": "package-a",
                            "Severity": "HIGH",
                            "Title": "package issue",
                            "FixedVersion": "2.0.0",
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trivy.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            findings = normalized_trivy(path, "trivy-source")
        self.assertEqual(findings[0]["finding_id"], "CVE-2099-0002")
        self.assertEqual(findings[0]["component"], "package-a")
        self.assertEqual(findings[0]["remediation"], "Upgrade to 2.0.0")


if __name__ == "__main__":
    unittest.main()
