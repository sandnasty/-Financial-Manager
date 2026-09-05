#!/usr/bin/env python3
"""Create and validate Financial Manager release provenance metadata."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def create_provenance(
    *,
    repository: str,
    source_sha: str,
    workflow: str,
    workflow_ref: str,
    run_id: str,
    run_attempt: str,
    image: str,
    digest: str,
    project_version: str,
    runner_os: str,
    runner_arch: str,
) -> dict[str, Any]:
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError("artifact digest must be a sha256 digest")
    if len(source_sha) != 40:
        raise ValueError("source SHA must be a full 40-character Git commit")

    return {
        "buildDefinition": {
            "buildType": "https://github.com/Financial-Manager/ci/immutable-container@v1",
            "externalParameters": {
                "repository": repository,
                "source_sha": source_sha,
                "project_version": project_version,
            },
            "internalParameters": {
                "workflow": workflow,
                "workflow_ref": workflow_ref,
                "run_id": run_id,
                "run_attempt": run_attempt,
            },
            "resolvedDependencies": [
                {
                    "uri": f"git+https://github.com/{repository}",
                    "digest": {"gitCommit": source_sha},
                }
            ],
        },
        "runDetails": {
            "builder": {
                "id": f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{run_attempt}"
            },
            "metadata": {
                "invocationId": f"{repository}:{run_id}:{run_attempt}",
                "startedOn": datetime.now(UTC).isoformat(),
            },
            "byproducts": [
                {
                    "name": "oci-image",
                    "uri": f"{image}@{digest}",
                    "digest": {"sha256": digest.removeprefix("sha256:")},
                },
                {
                    "name": "runner",
                    "value": {"os": runner_os, "arch": runner_arch},
                },
            ],
        },
    }


def validate_provenance(
    provenance: dict[str, Any], *, source_sha: str, digest: str, repository: str
) -> None:
    params = provenance["buildDefinition"]["externalParameters"]
    if params["repository"] != repository:
        raise ValueError("provenance repository mismatch")
    if params["source_sha"] != source_sha:
        raise ValueError("provenance source SHA mismatch")
    byproducts = provenance["runDetails"]["byproducts"]
    expected = digest.removeprefix("sha256:")
    if not any(
        item.get("name") == "oci-image"
        and item.get("digest", {}).get("sha256") == expected
        for item in byproducts
    ):
        raise ValueError("provenance artifact digest mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--project-version", required=True)
    parser.add_argument("--runner-os", required=True)
    parser.add_argument("--runner-arch", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    provenance = create_provenance(
        repository=args.repository,
        source_sha=args.source_sha,
        workflow=args.workflow,
        workflow_ref=args.workflow_ref,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        image=args.image,
        digest=args.digest,
        project_version=args.project_version,
        runner_os=args.runner_os,
        runner_arch=args.runner_arch,
    )
    validate_provenance(
        provenance,
        source_sha=args.source_sha,
        digest=args.digest,
        repository=args.repository,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
