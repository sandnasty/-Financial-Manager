# CI/CD identities, secrets, and permission separation

## Purpose

Financial Manager CI/CD uses GitHub Actions as the authoritative execution environment. Developer workstation credentials are not required for authoritative validation, artifact publication, or controlled promotion.

## Identity and permission model

### PR validation

Purpose: validate pull requests only.

Permissions:
- `contents: read`
- no package write
- no deployment write
- no OIDC token issuance

Checkout credentials are not persisted in the local Git configuration.

### Immutable artifact publication

Purpose: publish an already validated container artifact from `main` to GHCR.

Permissions:
- `contents: read`
- `packages: write` only in the publication job

Pull-request execution performs build verification only and does not publish. The workflow uses the short-lived GitHub Actions `GITHUB_TOKEN`; no long-lived registry password or PAT is required.

### DEV / TEST / PROD promotion

Purpose: consume an existing digest-qualified GHCR artifact without rebuilding it.

Permissions:
- `contents: read`
- `actions: read`
- `packages: read`

PROD additionally requires the GitHub `PROD` environment approval gate. Future persistent production credentials must be stored only as `PROD` environment secrets or obtained by short-lived federation from the PROD job. They must not be repository secrets if they are only needed for production.

## Secret handling rules

1. Never commit credentials, API keys, passwords, PATs, private keys, or production connection strings.
2. Use GitHub environment secrets for environment-specific credentials and repository secrets only when multiple controlled workflows genuinely require the same credential.
3. Prefer GitHub `GITHUB_TOKEN` or short-lived OIDC/federated credentials over static credentials.
4. Do not echo secret values, serialize them into deployment records, or upload them as artifacts.
5. Keep debug tracing disabled for steps that handle credentials.
6. Failure logs must identify the failed operation without printing secret material.
7. `.env` files and generated local secret material remain outside source control.

## Ownership and rotation

Current owner: repository/project owner until additional maintainers are assigned.

Rotation expectations:
- `GITHUB_TOKEN`: issued per workflow run; no manual rotation required.
- Future cloud or broker deployment credentials: prefer federation. If static credentials are unavoidable, rotate at least every 90 days and immediately after suspected disclosure or personnel/access changes.
- PROD credentials must be independently rotatable without modifying application source code or rebuilding artifacts.

Rotation procedure for a stored secret:
1. Create the replacement credential at the provider.
2. Update the corresponding GitHub Environment/Actions secret.
3. Run the narrowest non-production validation available, then a controlled promotion if required.
4. Revoke the old credential at the provider.
5. Record the rotation date and owner in the operational evidence system; never record the secret value.

## Emergency revocation

If credential exposure is suspected:
1. Revoke/disable the provider-side credential immediately.
2. Disable the affected GitHub environment or workflow if continued execution could cause harm.
3. Replace the credential or federation trust configuration.
4. Review Actions logs and deployment records for unauthorized use.
5. Re-run controlled validation/promotion with the replacement identity.
6. Capture incident evidence according to the E03 operational/audit procedures.

Revocation must not require an application source-code change. If revocation requires rebuilding application source, the credential architecture is considered non-compliant.

## Automated policy checks

`tests/test_cicd_security.py` guards the current baseline by verifying:
- PR validation remains read-only.
- PR checkout credentials are not persisted.
- only artifact publication has package write permission.
- promotion remains package-read-only and PROD-environment-gated.
- CI/CD workflows reference only the platform `GITHUB_TOKEN` today.
- common hard-coded credential patterns do not appear in authoritative CI/CD workflow definitions.

These tests run through the repository's existing `make validate` path and therefore execute on pull requests before merge.
