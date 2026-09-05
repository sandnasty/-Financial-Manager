# Retention and incident evidence

## Baseline

- Immutable audit events: 365 days online minimum.
- Logs, metrics, and traces: 90 days.
- Release, rollback, security, and incident evidence: 365 days.
- Capacity assumption: 100,000 audit events/day at 4 KiB each (about 146 GiB/year before
  indexes and backups); telemetry capacity is reviewed at 70 percent utilization.

Only a privileged operations role may archive data. Application and agent identities cannot
delete audit records. Expiry runs only after verified backup/export and writes its own audit
event. Legal hold overrides expiry.

## Evidence export

Export UTC timestamps, event/sequence IDs, correlation and trace IDs, actor identity, action,
result, service/version/environment, source commit, image digest, workflow/run identity,
payload and record hashes, relevant redacted logs, alert state, and operator decisions.
Create a manifest of SHA-256 digests, sign it using the platform evidence-signing workflow,
store it with least-privilege access, and record the export in the immutable audit store.

The exporter must recursively apply the same prohibited-field redaction used by telemetry
and audit producers. A second authorized person reviews any external disclosure.
