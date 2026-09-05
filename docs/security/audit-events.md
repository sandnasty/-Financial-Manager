# Audit events

The PostgreSQL `audit.events` relation is append-only for `fm_app`. Services call
`audit.append_event`; direct insert, update, delete, and truncate are denied.
The immutable event payload and each preceding record hash are incorporated into
the next record hash.

Audit data is retained for 365 days. Only an authorized operational retention
role may archive or expire records, and that action must be written to the audit
store before execution. Audit readers are least-privilege roles; exports include
event IDs, timestamps, correlation IDs, source version, immutable references,
and integrity hashes.

Never place credentials, secrets, authorization headers, cookies, tokens,
passwords, or full account numbers in audit details. The application redactor is
defense in depth; event producers remain responsible for data minimization.

A representative trade sequence uses one correlation ID across recommendation,
policy evaluation, human approval, brokerage handoff, and order-state events.
Ordering by `sequence_number` reconstructs the sequence without treating AI or
LLM output as authoritative approval.
