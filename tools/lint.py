#!/usr/bin/env python3
"""Run deterministic syntax, dependency-lock, and repository policy checks."""

from __future__ import annotations

import ast
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PINNED_FROM = re.compile(r"^FROM\s+[^\s:]+:[^\s@]+@sha256:[0-9a-f]{64}$", re.MULTILINE)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for path in sorted(ROOT.rglob("*.py")):
        if {"dist", ".venv", "__pycache__"}.intersection(path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(str(exc))

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "pylock.toml").read_text(encoding="utf-8"))
    if project["project"]["requires-python"] != "==3.14.7":
        fail("pyproject.toml must pin Python to ==3.14.7")
    expected_dependencies = ["boto3==1.43.89"]
    if project["project"]["dependencies"] != expected_dependencies:
        fail("pyproject dependencies changed; regenerate and commit pylock.toml")
    locked = {f'{package["name"]}=={package["version"]}' for package in lock.get("packages", [])}
    expected_locked = {
        "boto3==1.43.89",
        "botocore==1.43.89",
        "jmespath==1.1.0",
        "python-dateutil==2.9.0.post0",
        "s3transfer==0.19.2",
        "six==1.17.0",
        "urllib3==2.7.0",
    }
    if locked != expected_locked:
        fail("pylock.toml must exactly match the pinned Amazon SNS SDK dependency set")
    if lock.get("environments") != ["python_full_version == '3.14.7'"]:
        fail("pylock.toml must pin the exact Python environment")
    if lock.get("requires-python") != "==3.14.7":
        fail("pylock.toml must pin requires-python to ==3.14.7")

    dockerfile = (ROOT / "infra/container/Dockerfile").read_text(encoding="utf-8")
    if not PINNED_FROM.search(dockerfile):
        fail("Docker base image must use an explicit tag and sha256 digest")
    print("PASS: Python syntax, dependency lock, and container pin are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
