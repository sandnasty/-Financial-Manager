#!/usr/bin/env python3
"""Fail closed when the active Python does not match the source-controlled pin."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def required_python() -> tuple[int, int, int]:
    value = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    try:
        parts = tuple(int(part) for part in value.split("."))
    except ValueError as exc:
        raise SystemExit(f"FAIL: invalid .python-version value: {value!r}") from exc
    if len(parts) != 3:
        raise SystemExit(f"FAIL: expected an exact X.Y.Z Python pin, found {value!r}")
    return parts  # type: ignore[return-value]


def main() -> int:
    required = required_python()
    actual = sys.version_info[:3]
    if actual != required:
        expected = ".".join(map(str, required))
        found = ".".join(map(str, actual))
        print(
            f"FAIL: Python {expected} is required; found {found}. "
            "Install/activate the pinned version from .python-version.",
            file=sys.stderr,
        )
        return 2
    print(f"PASS: Python {'.'.join(map(str, actual))} matches the repository pin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
