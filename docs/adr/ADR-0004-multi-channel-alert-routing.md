# ADR-0004: Multi-channel production alert routing

- Status: Accepted
- Date: 2026-09-05
- Decision owner: Project owner
- Linear issue: MS-96

## Context

The MS-70 tabletop found that alert rules, ownership, and runbooks existed without a configured
production notification path. The owner selected optional email and SMS delivery and approved
the initial severity policy: High by email, Critical by email and SMS.

## Decision

Alertmanager groups High and Critical conditions and forwards them to an internal alert-router.
The router applies source-controlled policy, retries each provider up to three times, uses SMS as
fallback when High email delivery fails, emits delivery metrics and immutable audit events, and
raises a delivery failure when no operator path succeeds.

Destinations and provider credentials are injected only at runtime through the MS-61 secret
boundary. Email addresses, telephone numbers, tokens, and passwords are prohibited from source,
images, telemetry, and evidence bundles. Provider adapters remain replaceable.

## Consequences

- High alerts use email by default and fall back to SMS after exhausted retries.
- Critical alerts attempt email and SMS independently.
- Provider/destination activation can occur without rebuilding application source.
- A real production delivery exercise still requires owner-supplied destination values and
  provider credentials before live trading can be enabled.

## Verification

Contract and unit tests cover the Alertmanager handoff, severity routing, retries, fallback,
dual-channel Critical delivery, failure metrics, audit evidence, and absence of embedded secrets.
