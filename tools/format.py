#!/usr/bin/env python3
"""Apply the repository's dependency-free text normalization policy."""

from __future__ import annotations

import argparse
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUFFIXES = {".py", ".sh", ".md", ".toml", ".yaml", ".yml"}
NAMES = {"Makefile", ".python-version", ".tool-versions", ".gitattributes", ".env.example"}
IGNORED_PARTS = {".git", ".venv", "dist", "__pycache__"}


def candidates() -> list[pathlib.Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not IGNORED_PARTS.intersection(path.parts)
        and (path.suffix in SUFFIXES or path.name in NAMES)
    )


def normalized(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed: list[pathlib.Path] = []
    for path in candidates():
        original = path.read_text(encoding="utf-8")
        formatted = normalized(original)
        if original != formatted:
            changed.append(path.relative_to(ROOT))
            if not args.check:
                path.write_text(formatted, encoding="utf-8", newline="\n")
    if changed and args.check:
        print("FAIL: formatting required: " + ", ".join(map(str, changed)))
        return 1
    action = "checked" if args.check else "formatted"
    print(f"PASS: {action} {len(candidates())} source-controlled text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
