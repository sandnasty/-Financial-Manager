#!/usr/bin/env python3
"""Normalize security scanner results, apply approved exceptions, and enforce gates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

BLOCKING_SEVERITIES = {"HIGH", "CRITICAL"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_exceptions(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("schema_version") != 1:
        raise ValueError("security exception registry schema_version must be 1")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise ValueError("security exception registry must contain an exceptions list")

    today = date.today()
    validated: list[dict[str, Any]] = []
    required = {
        "scanner",
        "finding_id",
        "owner",
        "rationale",
        "approved_by",
        "review_on",
        "expires_on",
    }
    for index, item in enumerate(exceptions):
        if not isinstance(item, dict):
            raise ValueError(f"exception {index} must be an object")
        missing = sorted(required - item.keys())
        if missing:
            raise ValueError(f"exception {index} missing fields: {', '.join(missing)}")
        if not all(str(item[field]).strip() for field in required):
            raise ValueError(f"exception {index} contains an empty required field")
        review_on = date.fromisoformat(str(item["review_on"]))
        expires_on = date.fromisoformat(str(item["expires_on"]))
        if review_on > expires_on:
            raise ValueError(f"exception {index} review_on must not be after expires_on")
        if today > expires_on:
            raise ValueError(f"exception {index} expired on {expires_on.isoformat()}")
        if today > review_on:
            raise ValueError(
                f"exception {index} requires review; review_on was {review_on.isoformat()}"
            )
        validated.append(item)
    return validated


def normalized_bandit(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    findings = []
    for issue in data.get("results", []):
        findings.append(
            {
                "scanner": "bandit",
                "finding_id": str(issue.get("test_id", "UNKNOWN")),
                "severity": str(issue.get("issue_severity", "UNKNOWN")).upper(),
                "component": str(issue.get("filename", "unknown")),
                "title": str(issue.get("test_name", issue.get("issue_text", "Bandit finding"))),
                "remediation": str(issue.get("more_info", "Review the Bandit finding and remediate the unsafe pattern.")),
                "location": f"{issue.get('filename', 'unknown')}:{issue.get('line_number', '?')}",
            }
        )
    return findings


def normalized_trivy(path: Path, scanner_name: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    findings: list[dict[str, Any]] = []
    for result in data.get("Results", []) or []:
        target = str(result.get("Target", "unknown"))
        for vuln in result.get("Vulnerabilities", []) or []:
            findings.append(
                {
                    "scanner": scanner_name,
                    "finding_id": str(vuln.get("VulnerabilityID", "UNKNOWN")),
                    "severity": str(vuln.get("Severity", "UNKNOWN")).upper(),
                    "component": str(vuln.get("PkgName", target)),
                    "title": str(vuln.get("Title", vuln.get("VulnerabilityID", "Trivy vulnerability"))),
                    "remediation": (
                        f"Upgrade to {vuln.get('FixedVersion')}" if vuln.get("FixedVersion") else str(vuln.get("PrimaryURL", "Review the vulnerability advisory."))
                    ),
                    "location": target,
                }
            )
        for misconfig in result.get("Misconfigurations", []) or []:
            findings.append(
                {
                    "scanner": scanner_name,
                    "finding_id": str(misconfig.get("ID", "UNKNOWN")),
                    "severity": str(misconfig.get("Severity", "UNKNOWN")).upper(),
                    "component": target,
                    "title": str(misconfig.get("Title", "Trivy misconfiguration")),
                    "remediation": str(misconfig.get("Resolution", misconfig.get("Message", "Correct the configuration."))),
                    "location": target,
                }
            )
        for secret in result.get("Secrets", []) or []:
            findings.append(
                {
                    "scanner": scanner_name,
                    "finding_id": str(secret.get("RuleID", "SECRET")),
                    "severity": "CRITICAL",
                    "component": target,
                    "title": str(secret.get("Title", "Potential secret")),
                    "remediation": "Remove and revoke the secret, then rotate the affected credential.",
                    "location": f"{target}:{secret.get('StartLine', '?')}",
                }
            )
    return findings


def normalized_gitleaks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("gitleaks report must be a JSON list")
    findings = []
    for leak in data:
        findings.append(
            {
                "scanner": "gitleaks-history",
                "finding_id": str(leak.get("RuleID", "SECRET")),
                "severity": "CRITICAL",
                "component": str(leak.get("File", "unknown")),
                "title": str(leak.get("Description", "Secret detected in repository history")),
                "remediation": "Remove the secret from active source, revoke/rotate it, and assess history cleanup requirements.",
                "location": f"{leak.get('File', 'unknown')}:{leak.get('StartLine', '?')}",
                "fingerprint": str(leak.get("Fingerprint", "")),
            }
        )
    return findings


def exception_matches(finding: dict[str, Any], exception: dict[str, Any]) -> bool:
    if str(exception["scanner"]) != str(finding["scanner"]):
        return False
    if str(exception["finding_id"]) != str(finding["finding_id"]):
        return False
    component = exception.get("component")
    return component in (None, "", finding.get("component"))


def evaluate(
    findings: list[dict[str, Any]], exceptions: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocked: list[dict[str, Any]] = []
    excepted: list[dict[str, Any]] = []
    for finding in findings:
        if finding.get("severity") not in BLOCKING_SEVERITIES:
            continue
        matched = next(
            (item for item in exceptions if exception_matches(finding, item)), None
        )
        if matched:
            enriched = dict(finding)
            enriched["exception"] = {
                "owner": matched["owner"],
                "rationale": matched["rationale"],
                "approved_by": matched["approved_by"],
                "review_on": matched["review_on"],
                "expires_on": matched["expires_on"],
            }
            excepted.append(enriched)
        else:
            blocked.append(finding)
    return blocked, excepted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exceptions", required=True, type=Path)
    parser.add_argument("--bandit", type=Path)
    parser.add_argument("--trivy", type=Path)
    parser.add_argument("--trivy-scanner", default="trivy-source")
    parser.add_argument("--gitleaks", type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--build-run-id")
    parser.add_argument("--artifact-digest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        exceptions = validate_exceptions(load_json(args.exceptions))
        findings: list[dict[str, Any]] = []
        if args.bandit:
            findings.extend(normalized_bandit(args.bandit))
        if args.trivy:
            findings.extend(normalized_trivy(args.trivy, args.trivy_scanner))
        if args.gitleaks:
            findings.extend(normalized_gitleaks(args.gitleaks))
        blocked, excepted = evaluate(findings, exceptions)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"SECURITY GATE ERROR: {exc}", file=sys.stderr)
        return 2

    summary = {
        "schema_version": 1,
        "source_sha": args.source_sha,
        "build_run_id": args.build_run_id,
        "artifact_digest": args.artifact_digest,
        "blocking_severities": sorted(BLOCKING_SEVERITIES),
        "finding_count": len(findings),
        "blocking_count": len(blocked),
        "excepted_count": len(excepted),
        "blocked_findings": blocked,
        "excepted_findings": excepted,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    for finding in blocked:
        print(
            "BLOCK: "
            f"{finding['scanner']} {finding['severity']} {finding['finding_id']} "
            f"component={finding['component']} location={finding['location']} "
            f"remediation={finding['remediation']}",
            file=sys.stderr,
        )
    for finding in excepted:
        print(
            "EXCEPTION: "
            f"{finding['scanner']} {finding['finding_id']} owner={finding['exception']['owner']} "
            f"expires={finding['exception']['expires_on']}"
        )

    if blocked:
        print(f"SECURITY GATE FAILED: {len(blocked)} unexcepted High/Critical finding(s)")
        return 1
    print(
        "SECURITY GATE PASS: "
        f"{len(findings)} total finding(s), {len(excepted)} approved exception(s), "
        "0 unexcepted High/Critical findings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
