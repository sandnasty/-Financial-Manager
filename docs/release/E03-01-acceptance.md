# E03-01 end-to-end acceptance evidence

This record consolidates the acceptance evidence for E03-01 — Establish CI/CD and reproducible build pipeline.

## Baseline decisions

- Repository: `sandnasty/-Financial-Manager`
- Default branch: `main`
- CI: GitHub Actions
- Registry: GHCR
- Merge strategy: squash merge
- Runtime: Python 3.14.7
- Build interface: top-level `Makefile`
- Authoritative local/CI validation: `make validate`
- Artifact identity: semantic version + source SHA + CI run identity; deployment authority is OCI digest
- Promotion: immutable digest DEV -> TEST -> controlled PROD

## Scenario 1 — clean runner build/test/package

Evidence:
- MS-72 completed the deterministic local/clean-runner validation path.
- PR Validation uses a GitHub-hosted clean runner and executes `make validate`.
- MS-76 PR Validation run `33943571734` completed successfully after running the full validation suite, including reproducible build and CI/CD security contract tests.

Result: PASS.

## Scenario 2 — successful build publishes immutable artifact

Evidence:
- MS-74 implementation PR #6 merged successfully.
- Publication run `33940604193` published `ghcr.io/sandnasty/financial-manager` from source SHA `1401c03a75ee1b5abbb413f15eb4815fa533570f`.
- Recorded digest: `sha256:74e9f7a6e3decf927cbf5099735c55163638b1c4471c9837bf43d114f417d205`.
- Metadata artifact `immutable-container-metadata-33940604193-1` captured version, source SHA, run identity, tag, and digest.
- Subsequent `main` publication runs continued to pass after MS-75/MS-76 hardening.

Result: PASS.

## Scenario 3 — exact artifact moves DEV -> TEST without rebuild

Evidence:
- Controlled Artifact Promotion run `33940893091` resolved publication run `33940870041`.
- DEV pulled the digest-qualified artifact, started it, and passed `/health`.
- TEST ran only after DEV success and used the same resolved immutable reference.
- DEV record artifact: `deployment-record-DEV-33940893091`.
- TEST record artifact: `deployment-record-TEST-33940893091`.
- Promotion workflow contains no container build step.

Result: PASS.

## Scenario 4 — PROD requires explicit controlled approval

Evidence:
- Manual Controlled Artifact Promotion run `33942605567` was launched from `main` with explicit `PROMOTE` confirmation.
- DEV and TEST succeeded first.
- PROD was held behind the GitHub `PROD` environment required-reviewer gate and proceeded only after the project owner approved it.
- PROD verified the exact immutable reference without rebuilding:
  `ghcr.io/sandnasty/financial-manager@sha256:dab4fb039f4615117db0ef21fe2be64bf3069c3392f9bca2403dc20702051b59`.
- PROD deployment record: `deployment-record-PROD-33942605567`.

Result: PASS.

## Scenario 5 — failing mandatory test blocks merge/release

Evidence:
- PR #5 intentionally introduced a failing unit test against current `main`.
- GitHub Actions `PR Validation` job `validate` failed as intended.
- Raw PR state reported `mergeable_state="unstable"`, distinguishing conflict-free code from failed required checks.
- Project owner confirmed the required status-check gate was enabled on `main`.
- The negative-test PR was closed without merge.

Result: PASS.

## Scenario 6 — unapproved/direct PROD deployment cannot bypass controlled workflow

Evidence:
- Automatic publication-triggered promotion run `33940893091` completed DEV and TEST while the PROD job was skipped.
- PROD is only eligible on manual `workflow_dispatch` with `promote_to_prod=true` and confirmation `PROMOTE`.
- The eligible PROD job also declares `environment: PROD`; GitHub withheld execution until required-reviewer approval during run `33942605567`.
- No ordinary developer workstation or PR validation path has production deployment credentials or write permissions.

Result: PASS.

## Scenario 7 — secrets are isolated and masked

Evidence:
- PR Validation has `contents: read` only and checkout uses `persist-credentials: false`.
- Artifact publication has `packages: write` only in the controlled publication job.
- Promotion has `actions: read`, `contents: read`, and `packages: read`.
- Accepted PROD logs show authentication password rendered as `***` and no package write permission.
- `tests/test_cicd_security.py` rejects non-platform secret references and common hard-coded token/credential patterns in authoritative workflows.
- Current CI/CD uses the short-lived GitHub Actions `GITHUB_TOKEN`; no developer PAT or static registry credential is required.

Result: PASS.

## Documentation acceptance

Developer workflow:
- `docs/development/build-and-test.md`
- `docs/development/ci.md`
- `docs/development/developer-release-workflow.md`

Release workflow:
- `docs/release/artifact-publication.md`
- `docs/release/artifact-promotion.md`
- this acceptance record

Credential responsibilities:
- `docs/security/cicd-identities-secrets.md`

Result: PASS.

## Gap review

No blocking E03-01 acceptance gap remains based on the completed demonstrations above.

Known follow-on work is already represented by the remaining E03 issues for security scanning, SBOM/signing/provenance, audit storage, observability, rollback/kill controls, and operational runbooks. Those are intentionally outside the E03-01 baseline rather than hidden gaps in this acceptance record.

## E03-01 disposition

E03-01 is ready to close when this acceptance record and workflow documentation pass the normal pull-request validation pipeline and merge to `main`.
