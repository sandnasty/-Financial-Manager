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

Amazon SNS is the selected SMS provider. The alert-router publishes transactional messages
directly to the protected destination in E.164 format, uses the registered toll-free origination
number when configured, limits messages to one 140-character ASCII part, and applies a configurable
per-message price ceiling. The adapter returns the SNS `MessageId` as its auditable provider
receipt. It authenticates with the AWS SDK default IAM credential chain; long-lived AWS access keys
are not application secrets and must not be stored in GitHub.

## Consequences

- High alerts use email by default and fall back to SMS after exhausted retries.
- Critical alerts attempt email and SMS independently.
- Provider/destination activation can occur without rebuilding application source.
- The alert-router has egress only to the regional SNS API endpoint.
- The workload IAM role receives only `sns:Publish`; direct-to-phone publishing requires the
  policy resource to be `*`, so the role must not be shared with other services.
- A real production delivery exercise still requires owner-supplied destination values and
  a registered AWS origination number before live trading can be enabled.

## Verification

Contract and unit tests cover the Alertmanager handoff, severity routing, retries, fallback,
dual-channel Critical delivery, failure metrics, audit evidence, and absence of embedded secrets.
Provider tests cover E.164 validation, transactional delivery, origination-number selection,
one-part message limits, price caps, IAM client construction, and receipt validation.
