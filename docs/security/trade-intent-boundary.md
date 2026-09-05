# Signed TradeIntent trust boundary

TradeIntent v1 is the sole authenticated message accepted by the future broker gateway. AI/LLM
agents may propose structured inputs, but cannot approve, sign, or directly submit an executable
intent. Phase 1 remains U.S.-listed equities, long-only, no leverage or options, regular market
hours; downstream risk policy remains authoritative over any recommendation.

## Trust path

1. A recommendation produces a stable thesis and immutable recommendation event.
2. The deterministic risk service records its policy-versioned decision.
3. An authorized human approves a specific payload at L2.
4. `approval-service` binds the approver, approval record, risk version, expiration, and event
   provenance into the signed canonical payload.
5. `broker-gateway` accepts only a request from the approval-service network path, validates the
   schema and 15-minute lifetime, verifies the signature through the approval-service capability,
   checks operational kill controls and the current deterministic risk policy, and records the
   accepted intent.

The initial authentication mechanism is HMAC-SHA-256 with at least 256 bits of random key
material injected as `TRADEINTENT_SIGNING_KEY` under MS-61. Key material exists only inside the
approval service. The broker receives a verification capability, not the key. A managed
asymmetric signing service may replace this adapter later without changing the versioned payload
or broker contract.

## Replay and idempotency

The broker stores the intent ID, canonical-payload digest, and returned order reference before
downstream submission. An identical signed retry returns the same reference. Reuse of an intent
ID with changed content or an invalid signature fails closed. Expired, stale, malformed,
unsupported, unsigned, unapproved, policy-rejected, or operationally disabled intents fail.

## Audit chain

The accepted event preserves correlation ID, recommendation event, risk-decision event, human
approval and approver, TradeIntent ID, and later order/fill references. Secret values and signing
material never enter the record.

## Verification

`tests/test_trade_intent.py` covers valid acceptance, human/signing authorization, alteration,
expiration, replay/idempotency, direct-agent denial, current-risk rejection, kill controls,
required provenance, and schema presence.
