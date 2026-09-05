# Automated security scanning gates

## Purpose

Financial Manager blocks ordinary merge/promotion when an unexcepted High or Critical security finding is detected. Scan evidence is retained and traceable to the source SHA and, for container scans, the published artifact digest.

## Required scans

### Pull-request source gate

The existing required `PR Validation / validate` job performs:

1. **Bandit 1.9.4** — Python SAST over application/tooling Python source.
2. **Trivy** — filesystem dependency/SCA, secret, and configuration/misconfiguration scanning.
3. **Gitleaks 8.30.1** — full Git history secret detection (`fetch-depth: 0`).
4. **Security gate normalization** — `tools/security_gate.py` normalizes scanner results, applies approved exceptions, and fails the required PR job for unexcepted High/Critical findings. Secret findings are treated as Critical.

Raw machine-readable results and the normalized gate summary are uploaded with PR validation evidence for 90 days.

### Exact-image promotion gate

Before DEV receives a published artifact, `Controlled Artifact Promotion`:

1. resolves the immutable GHCR digest from MS-74 publication metadata;
2. verifies that digest exists;
3. runs Trivy against **that exact digest-qualified reference**;
4. normalizes the result through the same exception registry;
5. blocks DEV, TEST, and PROD if any unexcepted High/Critical container vulnerability remains;
6. retains the raw container scan and normalized summary for 90 days.

Promotion never rebuilds an image for scanning.

## Severity policy

- **Critical**: blocking.
- **High**: blocking.
- Medium/Low/Unknown: retained for visibility but do not block this baseline gate.
- Any detected secret from Trivy or Gitleaks is treated as Critical.

A scanner execution/configuration error fails the pipeline rather than being interpreted as a clean scan.

## Findings and remediation evidence

Raw scanner reports retain component/location, vulnerability or rule ID, severity, and scanner-provided remediation/advisory fields. `security-gate-summary.json` additionally normalizes blocking findings into:

- scanner;
- finding ID;
- severity;
- component;
- source location/target;
- title;
- remediation path.

The summary also records source SHA, CI/build run ID, and artifact digest where applicable.

## Approved exception process

Exceptions are source-controlled in `security/security-exceptions.json`, but an exception never contains a credential or secret value.

Each exception requires:

- `scanner` — normalized scanner name such as `trivy-source`, `trivy-container`, `bandit`, or `gitleaks-history`;
- `finding_id` — CVE/rule/test identifier;
- optional `component` — narrows the exception to one package/file/target;
- `owner` — person responsible for remediation;
- `rationale` — why temporary acceptance is justified;
- `approved_by` — approving release/security authority;
- `review_on` — next mandatory review date (`YYYY-MM-DD`);
- `expires_on` — hard expiration date (`YYYY-MM-DD`).

The gate rejects an exception when:

- required metadata is missing;
- the review date has passed;
- the expiration date has passed;
- the finding/scanner/component does not match.

Therefore exceptions fail closed and require periodic re-approval rather than becoming permanent suppressions.

Example structure (illustrative IDs only):

```json
{
  "scanner": "trivy-container",
  "finding_id": "CVE-2099-0001",
  "component": "example-package",
  "owner": "security-owner",
  "rationale": "No fixed upstream version; compensating control documented",
  "approved_by": "release-owner",
  "review_on": "2099-01-15",
  "expires_on": "2099-02-01"
}
```

## Secret response

A real secret finding is not normally an exception candidate. Remove it from active source, revoke/rotate the credential, assess repository-history cleanup, and follow `docs/security/cicd-identities-secrets.md` for emergency revocation.

## Traceability

PR source evidence artifact name:

`pr-validation-evidence-<github-run-id>`

Exact-digest container evidence artifact name:

`container-security-<publication-run-id>-<promotion-run-id>`

Together with source SHA, artifact publication metadata, and deployment records, these establish the chain:

`source SHA -> PR security evidence -> CI publication run -> OCI digest -> container security evidence -> DEV/TEST/PROD promotion records`.
