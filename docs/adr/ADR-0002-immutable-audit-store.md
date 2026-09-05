# ADR-0002 — Immutable Audit Event Store

Status: Accepted
Date: 2026-09-05
Decision owner: Owner/Human
Related: Linear MS-66, E03-04

## Context

Financial Manager must reconstruct security, policy, agent, TradeIntent, and
brokerage decisions without allowing ordinary application identities to rewrite
history.

## Decision

Use PostgreSQL as the initial authoritative audit store. Application identities
may append through a `SECURITY DEFINER` function and read authorized events, but
cannot directly insert, update, delete, or truncate records. A database trigger
rejects mutation even if privileges drift. Events form a SHA-256 hash chain so
privileged or offline replacement is detectable.

The canonical schema carries actor/agent identity, action, target, result,
correlation and trace identifiers, service/version/environment, immutable
references, and redacted details. Audit records are retained for one year.
Expiry is a privileged operational action, outside the application role, and
must itself be audited. The exact archival mechanism is finalized in MS-70.

## Alternatives considered

1. Application log files — rejected because application processes could rewrite
   them and correlation/query behavior would be weak.
2. SQLite — rejected because the selected platform baseline uses PostgreSQL and
   requires a separately enforceable application privilege boundary.
3. External ledger service — deferred because it adds unnecessary M1 complexity.

## Security and operational impact

Sensitive keys are recursively redacted before persistence. Secret values,
credentials, authorization headers, cookies, tokens, passwords, and account
numbers are prohibited. Database ownership and retention credentials are not
available to services or agents. Hash-chain verification and protected backups
provide detection beyond application-level immutability.

## Verification

- `infra/postgres/audit.sql`
- `financial_manager/audit.py`
- `tests/test_audit_store.py`
- `docs/security/audit-events.md`
