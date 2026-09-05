# Financial Manager developer and release workflow

This document is the repeatable E03-01 workflow for changing Financial Manager from a developer workstation through controlled production promotion.

## 1. Prepare the local environment

Supported baseline:
- Python 3.14.7
- GNU Make 4.3
- Windows development with WSL2/Docker Desktop supported

Run the environment diagnostic when needed:

```sh
make doctor
```

Run the authoritative local validation before opening a pull request:

```sh
make validate
```

`make validate` checks the pinned toolchain, repository policy, formatting, unit tests, security/CI contracts, and reproducible build output. A non-zero exit means the change is not ready for review.

For deeper details see `docs/development/build-and-test.md`.

## 2. Branch and pull-request workflow

1. Start from current `main`.
2. Create a feature branch associated with a Linear issue.
3. Make the change and run `make validate` locally.
4. Push the feature branch and open a pull request to `main`.
5. GitHub automatically runs `PR Validation` and applicable container verification.
6. Do not merge while a mandatory check is failing.
7. Use squash merge after required checks pass.

`PR Validation` is intentionally read-only. It cannot publish packages or deploy to environments, and checkout credentials are not persisted.

### Interpreting CI failures

- `check-toolchain`: local/runner runtime does not match the pinned version.
- `lint`: repository or source policy violation.
- `format-check`: source-controlled text needs normalization.
- `test`: unit/security/build-contract test failure.
- `build`: deterministic packaging/reproducibility failure.
- container verification: Dockerfile/base/runtime/container baseline problem.

Fix the underlying problem on the feature branch and push a new revision. Do not bypass the check.

## 3. Artifact publication

A successful merge to `main` triggers `Immutable Container Artifact`.

The publication workflow:
1. Checks out the exact `main` SHA.
2. Re-runs `make validate`.
3. Authenticates to GHCR using the short-lived GitHub Actions token.
4. Builds the representative container from the digest-pinned Docker base image.
5. Publishes a unique tag containing semantic version, full source SHA, workflow run ID, and attempt.
6. Records the immutable OCI digest.
7. Uploads `artifact-metadata.json` for downstream promotion.

The authoritative deployment identity is the digest-qualified reference:

```text
ghcr.io/sandnasty/financial-manager@sha256:<digest>
```

The mutable `latest` tag is not used as an authoritative release identity.

See `docs/release/artifact-publication.md`.

## 4. DEV and TEST promotion

After successful publication, `Controlled Artifact Promotion` resolves and validates the publication metadata, then:
1. Pulls the exact digest into DEV.
2. Starts the container and verifies `/health`.
3. Records the DEV deployment.
4. Only after DEV succeeds, pulls the same exact digest into TEST.
5. Starts the container and verifies `/health`.
6. Records the TEST deployment.

Promotion never rebuilds the artifact. A DEV failure stops TEST; a TEST failure prevents requested PROD promotion.

## 5. PROD promotion

PROD is never reached by the automatic publication path.

To request PROD promotion:
1. Open repository **Actions**.
2. Select **Controlled Artifact Promotion**.
3. Run the workflow from `main`.
4. Supply the successful publication run ID.
5. Set `promote_to_prod=true`.
6. Enter `PROMOTE` as the explicit confirmation.
7. DEV and TEST must succeed first.
8. The PROD job waits on the GitHub `PROD` environment required-reviewer gate.
9. An authorized reviewer approves the deployment.
10. The workflow verifies the same digest and records the approved PROD promotion baseline.

Future persistent production credentials belong only in the PROD environment and must not be exposed to ordinary validation or developer workstation flows.

See `docs/release/artifact-promotion.md` and `docs/security/cicd-identities-secrets.md`.

## 6. Rollback target identification

Each environment promotion stores a deployment record containing the artifact digest, version, source SHA/run, promotion run, actor, approval control, and timestamp.

To roll back, select a previously successful deployment record and promote its digest-qualified immutable reference. Do not rebuild old source to recreate a rollback artifact.

## 7. Security and credential responsibilities

- PR validation: read-only repository access.
- artifact publication: `contents: read`, `packages: write` only in the controlled publication job.
- DEV/TEST/PROD promotion: read-only repository/actions/package access.
- PROD: additional GitHub environment approval boundary.
- current registry auth: short-lived `GITHUB_TOKEN`; no developer PAT is required.
- future environment credentials: environment-scoped secrets or short-lived federation, with production-only credentials restricted to PROD.

Credential rotation and emergency revocation procedures are defined in `docs/security/cicd-identities-secrets.md`.

## 8. Evidence and troubleshooting

Every authoritative run records commit SHA and GitHub workflow/run identity. Publication and promotion also emit retained metadata/deployment-record artifacts.

When investigating a failure, begin with the relevant GitHub Actions run, identify the failed job/step, correlate it to the source SHA and Linear issue, and correct the source or platform configuration through the normal PR workflow.

The completed E03-01 acceptance evidence is recorded in `docs/release/E03-01-acceptance.md`.
