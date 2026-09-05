# Rollback and emergency controls

Only an authorized human operator may change controls. Agents and ordinary application
roles cannot invoke them. Every disable, rollback, or restoration is appended to the
immutable audit store.

## Emergency disable

Set global, agent-scoped, or TradeIntent submission state with explicit `CONFIRM` and
a reason. The guard is fail-closed: blocked actions do not continue downstream.
Visibility and historical audit access remain available.

## Rollback

Select the last approved digest from the deployment record. Dispatch `Controlled
Rollback`, enter the immutable digest, type `ROLLBACK`, obtain PROD environment
approval, and verify its signature before changing deployment. Validate health, audit
ingestion, telemetry, and policy version.

## Recovery and re-enable

Correct the cause, validate in DEV and TEST, obtain explicit operator approval, then
re-enable the narrowest affected scope with `CONFIRM`. Confirm queued actions cannot
duplicate a brokerage effect. Audit both disable and restoration.
