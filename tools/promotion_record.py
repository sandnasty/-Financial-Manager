#!/usr/bin/env python3
"""Validate immutable artifact metadata and write auditable promotion records."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path


DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def load_metadata(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("artifact metadata must be a JSON object")
    return data


def require_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"artifact metadata field {key!r} must be a non-empty string")
    return value


def validate_metadata(
    data: dict[str, object],
    *,
    expected_repository: str,
    expected_owner: str,
    expected_run_id: str,
) -> dict[str, str]:
    if data.get("schema_version") != 1:
        raise ValueError("unsupported artifact metadata schema version")
    if data.get("artifact_type") != "oci-container-image":
        raise ValueError("artifact metadata is not an OCI container image")

    image = require_string(data, "image")
    digest = require_string(data, "digest")
    immutable_ref = require_string(data, "immutable_ref")
    tagged_ref = require_string(data, "tagged_ref")
    tag = require_string(data, "tag")
    source_repository = require_string(data, "source_repository")
    source_sha = require_string(data, "source_sha")
    source_run_id = require_string(data, "run_id")
    project_version = require_string(data, "project_version")

    expected_image = f"ghcr.io/{expected_owner.lower()}/financial-manager"
    if image != expected_image:
        raise ValueError(f"unexpected image {image!r}; expected {expected_image!r}")
    if source_repository != expected_repository:
        raise ValueError("artifact source repository does not match promotion repository")
    if source_run_id != expected_run_id:
        raise ValueError("artifact run ID does not match requested publication run")
    if not DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("artifact digest is not a sha256 digest")
    if not SHA_PATTERN.fullmatch(source_sha):
        raise ValueError("artifact source SHA is not a full Git commit SHA")
    if immutable_ref != f"{image}@{digest}":
        raise ValueError("immutable_ref does not match image and digest")
    if tagged_ref != f"{image}:{tag}":
        raise ValueError("tagged_ref does not match image and tag")
    if tag == "latest" or tagged_ref.endswith(":latest"):
        raise ValueError("mutable latest tag cannot be promoted")

    return {
        "image": image,
        "digest": digest,
        "immutable_ref": immutable_ref,
        "tagged_ref": tagged_ref,
        "tag": tag,
        "source_repository": source_repository,
        "source_sha": source_sha,
        "source_run_id": source_run_id,
        "project_version": project_version,
    }


def write_github_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def resolve_command(args: argparse.Namespace) -> None:
    metadata = load_metadata(args.metadata)
    resolved = validate_metadata(
        metadata,
        expected_repository=args.repository,
        expected_owner=args.owner,
        expected_run_id=args.expected_run_id,
    )
    args.resolved_copy.parent.mkdir(parents=True, exist_ok=True)
    with args.resolved_copy.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    write_github_outputs(args.github_output, resolved)


def record_command(args: argparse.Namespace) -> None:
    metadata = load_metadata(args.metadata)
    resolved = validate_metadata(
        metadata,
        expected_repository=args.repository,
        expected_owner=args.owner,
        expected_run_id=args.source_run_id,
    )
    record = {
        "schema_version": 1,
        "record_type": "financial-manager-deployment",
        "environment": args.environment,
        "deployment_mode": args.deployment_mode,
        "artifact": {
            "immutable_ref": resolved["immutable_ref"],
            "digest": resolved["digest"],
            "tagged_ref": resolved["tagged_ref"],
            "project_version": resolved["project_version"],
            "source_repository": resolved["source_repository"],
            "source_sha": resolved["source_sha"],
            "source_run_id": resolved["source_run_id"],
        },
        "promotion": {
            "repository": args.repository,
            "run_id": args.promotion_run_id,
            "run_attempt": args.promotion_run_attempt,
            "requesting_actor": args.actor,
            "triggering_actor": args.triggering_actor,
            "approval_control": args.approval_control,
        },
        "recorded_at_utc": datetime.now(UTC).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--metadata", type=Path, required=True)
    resolve.add_argument("--repository", required=True)
    resolve.add_argument("--owner", required=True)
    resolve.add_argument("--expected-run-id", required=True)
    resolve.add_argument("--github-output", type=Path, required=True)
    resolve.add_argument("--resolved-copy", type=Path, required=True)
    resolve.set_defaults(function=resolve_command)

    record = subparsers.add_parser("record")
    record.add_argument("--metadata", type=Path, required=True)
    record.add_argument("--repository", required=True)
    record.add_argument("--owner", required=True)
    record.add_argument("--source-run-id", required=True)
    record.add_argument("--environment", required=True)
    record.add_argument("--deployment-mode", required=True)
    record.add_argument("--promotion-run-id", required=True)
    record.add_argument("--promotion-run-attempt", required=True)
    record.add_argument("--actor", required=True)
    record.add_argument("--triggering-actor", required=True)
    record.add_argument("--approval-control", required=True)
    record.add_argument("--output", type=Path, required=True)
    record.set_defaults(function=record_command)
    return result


def main() -> None:
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
