#!/usr/bin/env python3
"""Build a byte-for-byte reproducible archive of the representative service."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUTS = (
    pathlib.Path("financial_manager/__init__.py"),
    pathlib.Path("financial_manager/app.py"),
    pathlib.Path("financial_manager/notification_settings.py"),
    pathlib.Path("infra/container/baseline_service.py"),
    pathlib.Path("pyproject.toml"),
    pathlib.Path("pylock.toml"),
)
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(output: pathlib.Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = {path.as_posix(): (ROOT / path).read_bytes() for path in INPUTS}
    manifest = {
        "format": 1,
        "service": "financial-manager-baseline",
        "files": {name: sha256(data) for name, data in sorted(files.items())},
    }
    members = dict(files)
    members["build-manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return sha256(output.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "dist/baseline-service.zip")
    args = parser.parse_args()
    digest = build(args.output.resolve())
    print(f"PASS: built {args.output} sha256:{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
