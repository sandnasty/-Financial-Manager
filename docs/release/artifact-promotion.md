# Controlled DEV / TEST / PROD artifact promotion

MS-75 promotes the immutable OCI artifact produced by MS-74 without rebuilding it between environments.

## Promotion source

The promotion workflow consumes `artifact-metadata.json` from a successful `Immutable Container Artifact` workflow run. The metadata is validated before use:

- publication run ID must match the selected source run;
- source repository must be this repository;
- image must be `ghcr.io/<repository-owner>/financial-manager`;
- source SHA must be a full Git commit SHA;
- digest must be a full `sha256` digest;
- the digest-qualified immutable reference must exactly match the image and digest;
- `latest` is rejected.

No promotion job contains a container build step. The digest-qualified reference is carried unchanged through DEV, TEST, and PROD.

## DEV and TEST baseline deployments

A successful publication on `main` automatically starts `Controlled Artifact Promotion` through the `workflow_run` trigger.

DEV and TEST currently use isolated GitHub-hosted runners as the deployment baseline because a persistent application runtime has not yet been established. Each stage:

1. authenticates to GHCR with read-only package permissions;
2. pulls the exact digest-qualified image;
3. runs the container without rebuilding it;
4. verifies the `/health` endpoint;
5. removes the runner-local container;
6. writes and uploads a deployment record.

TEST depends on successful DEV completion. A failed DEV deployment prevents TEST. A failed TEST deployment prevents any requested PROD promotion.

When persistent DEV and TEST runtimes are introduced, their deployment adapters may replace the runner-local container step, but they must continue consuming the same immutable reference and preserving the deployment record contract.

## PROD approval boundary

PROD is deliberately not automatic. It is available only from a manual `workflow_dispatch` executed from `main`, with:

- a successful publication run ID;
- `promote_to_prod` explicitly enabled;
- `prod_confirmation` equal to `PROMOTE`;
- the GitHub `PROD` environment approval gate satisfied.

The `promote-prod` job declares `environment: PROD`. Configure the repository's `PROD` GitHub Environment with a required reviewer before using production promotion. Production credentials, when introduced, must be stored only as `PROD` environment secrets and must not be repository-level secrets or developer workstation credentials. This keeps ordinary developer workstations outside the production deployment boundary.

The current PROD stage records an approved promotion baseline and verifies that the exact digest still resolves in GHCR. It does not deploy to a persistent production runtime because one is not yet operational.

## Deployment records and approval evidence

Each successful environment stage uploads a JSON deployment record containing:

- environment;
- deployment mode;
- immutable image reference and digest;
- human-readable tagged reference and project version;
- source repository, commit SHA, and publication run ID;
- promotion workflow run ID and attempt;
- requesting and triggering GitHub actor;
- approval control used by the stage;
- UTC record timestamp.

For PROD, the deployment record identifies the approval control as `github-environment-required-reviewer`. The actual reviewer decision and reviewer identity remain part of GitHub's Environment deployment audit history; the workflow artifact supplements that platform audit with the exact artifact identity being approved.

## Rollback candidate identification

Every successful deployment record is retained as a workflow artifact for 90 days. To identify a rollback candidate, select the previous successful promotion run for the target environment and use its recorded `artifact.immutable_ref`. Rollback must promote that previously deployed digest; it must never rebuild the historical source revision.

A later operational-retention issue may extend or externalize deployment-record retention without changing this digest-based rollback rule.
