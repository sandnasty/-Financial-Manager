# Immutable container artifact publication

MS-74 defines how a validated Financial Manager revision becomes a deployable OCI container artifact.

## Registry and publishing authority

Authoritative container artifacts are published to GitHub Container Registry (GHCR) by GitHub Actions only. Developer workstations may build and run containers locally for diagnostics, but a locally produced image is never an authoritative release artifact.

The publishing workflow uses the repository-scoped `GITHUB_TOKEN` with `packages: write` permission only in the publish job. Pull-request verification jobs retain read-only repository permissions and never authenticate to GHCR.

## Source validation

Every publication from `main` reruns the authoritative repository validation command before registry authentication and image publication:

```sh
make validate
```

A failed build, test, lint, formatting, lock-file, or reproducibility check prevents publication.

## Artifact identity

The project semantic version is read from `pyproject.toml`. Each published tag also contains the full source commit SHA, GitHub Actions run ID, and run attempt:

```text
v<semver>-sha.<40-char-sha>-run.<run-id>-attempt.<attempt>
```

Example shape:

```text
v0.1.0-sha.0123456789abcdef0123456789abcdef01234567-run.123456789-attempt.1
```

This makes every CI publication uniquely identifiable. Re-running the same source revision produces a new run/attempt identity instead of silently replacing the prior tagged publication.

The `latest` tag is deliberately not published and must not be used as an authoritative deployment reference.

## Immutable deployment reference

After GHCR accepts the image, the workflow captures the registry-provided OCI digest. The digest-qualified reference is the authoritative deployment identity:

```text
ghcr.io/<owner>/financial-manager@sha256:<digest>
```

Tags support human navigation and traceability; downstream DEV/TEST/PROD promotion must consume the digest-qualified reference rather than resolving a mutable tag at deployment time.

## Metadata contract

Each successful publication produces `artifact-metadata.json` containing at least:

- schema version
- artifact type
- image name
- unique tag and tagged reference
- immutable registry digest and digest-qualified reference
- semantic project version
- source repository and commit SHA
- GitHub Actions workflow, run ID, run attempt, and run URL
- publication timestamp

The metadata file is uploaded as a GitHub Actions artifact for downstream promotion and deployment work. It is retained for 90 days at this stage; retention policy will be revisited with the operational runbook work.

## Relationship to later supply-chain controls

MS-74 intentionally establishes the immutable artifact and traceability boundary only. SBOM generation, artifact signing, and formal provenance/attestation are added under E03-03 without changing the rule that deployments identify artifacts by immutable digest.
