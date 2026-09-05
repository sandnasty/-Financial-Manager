import unittest
from pathlib import Path

from tools.promotion_record import validate_metadata


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "artifact-promotion.yml"


class PromotionWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_promotion_never_rebuilds_artifact(self) -> None:
        self.assertNotIn("docker build ", self.workflow)
        self.assertNotIn("docker/build-push-action", self.workflow)

    def test_successful_publication_triggers_dev_test_flow(self) -> None:
        self.assertIn("workflow_run:", self.workflow)
        self.assertIn("Immutable Container Artifact", self.workflow)
        self.assertIn("environment:\n      name: DEV", self.workflow)
        self.assertIn("environment:\n      name: TEST", self.workflow)

    def test_test_depends_on_dev(self) -> None:
        self.assertTrue(
            "- deploy-dev" in self.workflow
            or "needs: [resolve-artifact, deploy-dev]" in self.workflow
        )
        self.assertIn("Deploy the same exact digest to TEST runner", self.workflow)

    def test_prod_is_manual_and_environment_gated(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("inputs.promote_to_prod == true", self.workflow)
        self.assertIn("name: PROD", self.workflow)
        self.assertIn("prod_confirmation", self.workflow)
        self.assertIn("github-environment-required-reviewer", self.workflow)

    def test_promotion_uses_digest_qualified_reference(self) -> None:
        self.assertIn("immutable_ref", self.workflow)
        self.assertIn("docker pull \"${IMMUTABLE_REF}\"", self.workflow)
        self.assertNotIn(":latest", self.workflow)

    def test_each_environment_preserves_a_deployment_record(self) -> None:
        for environment in ("DEV", "TEST", "PROD"):
            self.assertIn(f"deployment-record-{environment}", self.workflow)


class PromotionMetadataValidationTests(unittest.TestCase):
    def metadata(self) -> dict[str, object]:
        digest = "sha256:" + "a" * 64
        image = "ghcr.io/sandnasty/financial-manager"
        tag = "v0.1.0-sha." + "b" * 40 + "-run.123-attempt.1"
        return {
            "schema_version": 1,
            "artifact_type": "oci-container-image",
            "image": image,
            "tag": tag,
            "tagged_ref": f"{image}:{tag}",
            "digest": digest,
            "immutable_ref": f"{image}@{digest}",
            "project_version": "0.1.0",
            "source_repository": "sandnasty/-Financial-Manager",
            "source_sha": "b" * 40,
            "run_id": "123",
        }

    def test_valid_metadata_resolves(self) -> None:
        resolved = validate_metadata(
            self.metadata(),
            expected_repository="sandnasty/-Financial-Manager",
            expected_owner="sandnasty",
            expected_run_id="123",
        )
        self.assertTrue(resolved["immutable_ref"].endswith("a" * 64))

    def test_wrong_source_run_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_metadata(
                self.metadata(),
                expected_repository="sandnasty/-Financial-Manager",
                expected_owner="sandnasty",
                expected_run_id="999",
            )

    def test_latest_tag_is_rejected(self) -> None:
        metadata = self.metadata()
        metadata["tag"] = "latest"
        metadata["tagged_ref"] = "ghcr.io/sandnasty/financial-manager:latest"
        with self.assertRaises(ValueError):
            validate_metadata(
                metadata,
                expected_repository="sandnasty/-Financial-Manager",
                expected_owner="sandnasty",
                expected_run_id="123",
            )


if __name__ == "__main__":
    unittest.main()
