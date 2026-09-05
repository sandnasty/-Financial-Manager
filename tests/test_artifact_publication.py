import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "artifact-publish.yml"
DOCKERFILE = ROOT / "infra" / "container" / "Dockerfile"


class ImmutableArtifactContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    def test_container_base_image_is_digest_pinned(self) -> None:
        first_line = self.dockerfile.splitlines()[0]
        self.assertIn("@sha256:", first_line)

    def test_publication_is_limited_to_main(self) -> None:
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn("packages: write", self.workflow)

    def test_artifact_identity_contains_source_and_run_identity(self) -> None:
        self.assertIn("${GITHUB_SHA}", self.workflow)
        self.assertIn("${GITHUB_RUN_ID}", self.workflow)
        self.assertIn("${GITHUB_RUN_ATTEMPT}", self.workflow)

    def test_digest_is_recorded_as_authoritative_identity(self) -> None:
        self.assertIn("steps.build.outputs.digest", self.workflow)
        self.assertIn("immutable_ref", self.workflow)
        self.assertIn("Authoritative deployment identity: digest", self.workflow)

    def test_latest_tag_is_never_published(self) -> None:
        self.assertNotIn(":latest", self.workflow)
        self.assertNotIn("tags: latest", self.workflow)

    def test_reruns_receive_unique_tags(self) -> None:
        self.assertIn("run.${GITHUB_RUN_ID}-attempt.${GITHUB_RUN_ATTEMPT}", self.workflow)


if __name__ == "__main__":
    unittest.main()
