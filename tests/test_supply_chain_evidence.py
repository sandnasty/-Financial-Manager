import unittest
from pathlib import Path

from tools.supply_chain_evidence import create_provenance, validate_provenance


ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / ".github" / "workflows" / "artifact-publish.yml"
PROMOTE = ROOT / ".github" / "workflows" / "artifact-promotion.yml"


class ProvenanceTests(unittest.TestCase):
    def provenance(self) -> dict:
        return create_provenance(
            repository="sandnasty/-Financial-Manager",
            source_sha="a" * 40,
            workflow="Immutable Container Artifact",
            workflow_ref="sandnasty/-Financial-Manager/.github/workflows/artifact-publish.yml@refs/heads/main",
            run_id="123",
            run_attempt="1",
            image="ghcr.io/sandnasty/financial-manager",
            digest="sha256:" + "b" * 64,
            project_version="0.1.0",
            runner_os="Linux",
            runner_arch="X64",
        )

    def test_provenance_binds_source_and_digest(self) -> None:
        data = self.provenance()
        validate_provenance(
            data,
            source_sha="a" * 40,
            digest="sha256:" + "b" * 64,
            repository="sandnasty/-Financial-Manager",
        )

    def test_replaced_digest_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_provenance(
                self.provenance(),
                source_sha="a" * 40,
                digest="sha256:" + "c" * 64,
                repository="sandnasty/-Financial-Manager",
            )


class SupplyChainWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publish = PUBLISH.read_text(encoding="utf-8")
        cls.promote = PROMOTE.read_text(encoding="utf-8")

    def test_publication_uses_keyless_signing_permission(self) -> None:
        self.assertIn("id-token: write", self.publish)
        self.assertIn("cosign-release: 'v3.1.3'", self.publish)
        self.assertIn("cosign sign --yes", self.publish)

    def test_publication_generates_sbom_and_provenance_attestations(self) -> None:
        self.assertIn("format: cyclonedx", self.publish)
        self.assertIn("--type cyclonedx", self.publish)
        self.assertIn("--type slsaprovenance", self.publish)
        self.assertIn("supply-chain-evidence/", self.publish)

    def test_promotion_verifies_signature_and_attestations_before_dev(self) -> None:
        self.assertIn("cosign verify", self.promote)
        self.assertIn("cosign verify-attestation", self.promote)
        verification = self.promote.index("Verify signature and supply-chain attestations")
        dev = self.promote.index("deploy-dev:")
        self.assertLess(verification, dev)

    def test_verification_is_bound_to_main_publication_workflow_identity(self) -> None:
        expected = "artifact-publish.yml@refs/heads/main"
        self.assertIn(expected, self.promote)
        self.assertIn("https://token.actions.githubusercontent.com", self.promote)


if __name__ == "__main__":
    unittest.main()
