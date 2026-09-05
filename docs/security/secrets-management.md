# Secrets management and rotation

## Decision

Financial Manager uses service-identity-scoped runtime injection. GitHub Environment secrets
are the current authoritative store for deployment credentials; provider-native short-lived
federation is preferred when available. Secret names and access policy are version controlled
in `config/secrets-policy.json`, but values never are.

The runtime variable contract is `FM_<ENVIRONMENT>_<SECRET_NAME>`. A service receives only the
variables allowed to its identity and environment. DEV, TEST, and PROD values are independent.
Only `broker-gateway` may receive `FM_PROD_BROKER_CREDENTIAL`; AI/LLM and agent services are
explicitly denied live-execution secrets.

## Handling requirements

- Inject values at container start through the deployment secret store. Never use Docker build
  arguments, image layers, source files, committed `.env` files, prompts, or workflow artifacts.
- Keep the environment-specific access mapping least-privilege and review policy changes by PR.
- Pass `SecretValue.reveal()` directly to the provider client boundary. Do not log, serialize,
  interpolate, or attach it to an exception.
- The audit stream records service identity, environment, secret name, result, reason, and time.
  It never records a secret value.
- The shared recursive redactor masks common secret-bearing keys in logs, telemetry, crash
  context, and diagnostic evidence.

## Rotation procedure

1. Create a replacement credential at the provider with no broader permissions than the old one.
2. Update the matching DEV or TEST protected secret and validate the narrow integration path.
3. Update PROD through its protected environment and required approval.
4. Verify authorized access and verify an unauthorized service remains denied.
5. Revoke the old provider credential.
6. Record actor, secret name, environment, timestamps, and results in the immutable audit store.

Static secrets rotate at least every 90 days. Suspected disclosure, ownership change, or scope
reduction requires immediate rotation.

## Revocation procedure

1. Disable the credential at the provider and invoke the operational kill control if execution
   could be unsafe.
2. Mark the secret revoked in the running secret-access boundary so further reads fail closed.
3. Remove or replace the protected environment value.
4. Review audit, workflow, and provider access evidence for unauthorized use.
5. Restore service only after a replacement passes DEV/TEST validation and PROD approval.

Revocation must not require source changes or an image rebuild.

## Verification

`tests/test_secrets.py` proves service and environment isolation, agent denial, missing-value
failure, safe representations, audit metadata without values, revocation, policy integrity, and
recursive redaction. Repository scanning continues to reject committed credential material.
