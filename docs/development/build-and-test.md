# Deterministic local build and test

MS-72 establishes one repository-root interface for developers and CI. The supported local environment is Windows with WSL2, Linux-style commands, and Docker Desktop using its WSL2 backend. macOS and Linux remain portability targets, but are not yet authoritative environments.

## Pinned inputs

- Python `3.14.7` is pinned in `.python-version`, `.tool-versions`, and `pyproject.toml`.
- GNU Make `4.3` is pinned in `.tool-versions`.
- Third-party Python dependencies are fully represented by `pylock.toml`. The Amazon SNS adapter
  uses the exactly pinned AWS SDK for Python dependency set; unit tests replace its network client
  with an in-memory contract double.
- The container base is pinned by both tag and multi-platform manifest digest in `infra/container/Dockerfile`.
- Source text is normalized to LF through `.gitattributes` and the formatter.

No validation command reads `.env`, global Python packages, IDE state, or machine-specific configuration. Generated artifacts are written beneath ignored `dist/`.

## Supported setup

1. Install WSL2 and a Linux distribution.
2. Install Docker Desktop for Windows and enable the WSL2 backend/integration.
3. Inside WSL2, install the exact versions in `.tool-versions` (an asdf-compatible version manager may be used).
4. From the repository root, run `make doctor` and resolve every FAIL. WARN is diagnostic and does not hide required-tool failures.

`make doctor` is read-only. It ends with PASS/WARN/FAIL counts and exits non-zero when a required tool is missing or mismatched.

## Authoritative validation command

From the repository root, run:

```sh
make validate
```

That single command checks the exact Python runtime, Python syntax, dependency-lock consistency, the pinned container base, repository formatting, all unit/build-contract tests, and finally creates `dist/baseline-service.zip`. The test path includes a byte-for-byte double-build comparison. Any failed check, test, or build exits non-zero.

CI must invoke this same command after activating Python `3.14.7`; it must not duplicate the individual steps in workflow YAML.

## Other top-level commands

- `make build` creates the deterministic representative-service archive.
- `make test` runs the complete unit and build-contract suite.
- `make lint` checks syntax, lock consistency, and container pinning.
- `make format` normalizes source-controlled text; `make format-check` is non-mutating.
- `make doctor` diagnoses WSL2, Python, GNU Make, Git, Docker, and Compose.
- `make container-test` runs the existing hardened-container integration test.
- `make clean` removes generated build outputs.

To prove clean-room behavior, start from a fresh checkout, activate the pinned tools, and run only `make validate`. No dependency installation is currently necessary because `pylock.toml` resolves to an empty package set. If a dependency is later added, update both `pyproject.toml` and `pylock.toml` in the same change; the validation policy deliberately fails on drift.
