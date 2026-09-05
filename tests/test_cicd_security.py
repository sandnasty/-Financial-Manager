import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PR_VALIDATION = WORKFLOWS / "pr-validation.yml"
ARTIFACT_PUBLISH = WORKFLOWS / "artifact-publish.yml"
ARTIFACT_PROMOTION = WORKFLOWS / "artifact-promotion.yml"


class CicdPermissionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pr = PR_VALIDATION.read_text(encoding="utf-8")
        cls.publish = ARTIFACT_PUBLISH.read_text(encoding="utf-8")
        cls.promote = ARTIFACT_PROMOTION.read_text(encoding="utf-8")

    def test_pr_validation_is_read_only(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.pr)
        self.assertNotIn("packages: write", self.pr)
        self.assertNotIn("deployments: write", self.pr)
        self.assertNotIn("id-token: write", self.pr)

    def test_pr_checkout_does_not_persist_credentials(self) -> None:
        self.assertIn("persist-credentials: false", self.pr)

    def test_publication_write_permission_is_registry_and_signing_scoped(self) -> None:
        self.assertIn("publish-container:", self.publish)
        self.assertIn("packages: write", self.publish)
        self.assertIn("id-token: write", self.publish)
        self.assertNotIn("contents: write", self.publish)
        self.assertNotIn("deployments: write", self.publish)
        verify_section = self.publish.split("verify-container:", 1)[1].split(
            "publish-container:", 1
        )[0]
        self.assertNotIn("id-token: write", verify_section)

    def test_promotion_is_read_only_and_prod_environment_gated(self) -> None:
        self.assertIn("packages: read", self.promote)
        self.assertNotIn("packages: write", self.promote)
        self.assertNotIn("contents: write", self.promote)
        self.assertNotIn("deployments: write", self.promote)
        self.assertNotIn("id-token: write", self.promote)
        self.assertIn("environment:\n      name: PROD", self.promote)
        self.assertIn("github-environment-required-reviewer", self.promote)

    def test_only_platform_token_is_referenced_in_cicd_workflows(self) -> None:
        combined = "\n".join((self.pr, self.publish, self.promote))
        refs = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", combined))
        self.assertEqual(refs, {"GITHUB_TOKEN"})

    def test_no_common_secret_literal_assignments_in_workflows(self) -> None:
        combined = "\n".join((self.pr, self.publish, self.promote))
        forbidden = (
            r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"][^$][^'\"]+",
            r"ghp_[A-Za-z0-9]{20,}",
            r"github_pat_[A-Za-z0-9_]{20,}",
        )
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, combined), pattern)


if __name__ == "__main__":
    unittest.main()
