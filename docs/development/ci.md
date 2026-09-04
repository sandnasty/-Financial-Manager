# Pull-request CI validation

MS-73 defines the source-controlled validation pipeline used for Financial Manager pull requests.

## Trigger and runner

`.github/workflows/pr-validation.yml` runs for pull requests targeting `main` when they are opened, synchronized, reopened, or marked ready for review. It may also be run manually with `workflow_dispatch` for diagnostics. Draft pull requests do not execute the validation job until marked ready.

The job runs on a clean GitHub-hosted `ubuntu-latest` runner with read-only repository permissions. It activates the pinned Python `3.14.7` runtime, verifies GNU Make `4.3`, and then invokes only the authoritative repository command:

```sh
make validate
```

The workflow deliberately does not duplicate lint, formatting, unit-test, lock-file, or deterministic-build logic in YAML; those checks remain owned by the MS-72 entry point.

## Failure, cancellation, and timeout behavior

- Any failure from `make validate` fails the CI job and returns a non-successful check result.
- Superseded runs for the same pull request are canceled through the workflow concurrency group.
- The validation job has a 10-minute timeout and does not retry failed validation automatically. A new commit, manual rerun, or reopened/ready-for-review event starts a fresh clean run.
- Logs use standard GitHub Actions output and do not print environment secrets. The job requires no repository secrets.

## Evidence and traceability

Every run records the repository, commit SHA, GitHub Actions run ID, run attempt, and workflow name in `ci-evidence.txt`. The workflow also publishes those identifiers to the GitHub Actions job summary and uploads the evidence file plus the deterministic build artifact when available. Evidence artifacts are retained for 30 days at this stage.

The authoritative release/deployment identity remains the source commit SHA; later artifact publication work under E03-01D will add immutable container digest and registry metadata.

## Required-check enforcement

The intended protected-branch control is to require the `PR Validation / validate` check before merging to `main`. As of MS-73 implementation, the repository is private and the connected GitHub account reports that repository rulesets/required-check enforcement requires GitHub Pro or making the repository public. Until the plan supports private-repository branch protection, the workflow still reports pass/fail truthfully but GitHub cannot enforce the check as a merge gate.

This is a platform limitation, not an authorization to bypass failed CI. Failed required validation must be treated as a no-merge condition by project policy until GitHub enforcement is available.
