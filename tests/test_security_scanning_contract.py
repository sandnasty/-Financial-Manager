import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PR_WORKFLOW = ROOT / ".github" / "workflows" / "pr-validation.yml"
PROMOTION_WORKFLOW = ROOT / ".github" / "workflows" / "artifact-promotion.yml"
EXCEPTIONS = ROOT / "security" / "security-exceptions.json"


class SecurityScanningWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pr = PR_WORKFLOW.read_text(encoding="utf-8")
        cls.promotion = PROMOTION_WORKFLOW.read_text(encoding="utf-8")

    def test_required_pr_gate_runs_sast_sca_secret_and_config_scans(self) -> None:
        self.assertIn("bandit==1.9.4", self.pr)
        self.assertIn("scanners: vuln,secret,misconfig", self.pr)
        self.assertIn("gitleaks:v8.30.1@sha256:", self.pr)
        self.assertIn("tools/security_gate.py", self.pr)

    def test_repository_history_is_available_to_secret_scan(self) -> None:
        self.assertIn("fetch-depth: 0", self.pr)
        self.assertIn("git /repo --redact", self.pr)

    def test_security_results_are_retained_with_pr_evidence(self) -> None:
        self.assertIn("security-results/", self.pr)
        self.assertIn("retention-days: 90", self.pr)

    def test_promotion_scans_exact_resolved_digest_before_dev(self) -> None:
        self.assertIn("image-ref: ${{ steps.resolve.outputs.immutable_ref }}", self.promotion)
        scan_index = self.promotion.index("Scan exact promotion digest")
        dev_index = self.promotion.index("deploy-dev:")
        self.assertLess(scan_index, dev_index)
        self.assertIn("--artifact-digest '${{ steps.resolve.outputs.digest }}'", self.promotion)
        self.assertIn("container-security-${{ steps.publication.outputs.run_id }}-${{ github.run_id }}", self.promotion)

    def test_exception_registry_exists(self) -> None:
        self.assertTrue(EXCEPTIONS.exists())


if __name__ == "__main__":
    unittest.main()
