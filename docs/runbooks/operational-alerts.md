# Operational alert response

Prometheus groups repeated conditions with identical labels; the `for` windows suppress
transient failures. Operators silence only during an approved change and must link the
silence to an audit event.

## Service down

Owner: Platform operator. Confirm the health endpoint, preserve logs and build identity,
stop unsafe downstream actions, and use the MS-69 rollback procedure if applicable.

## Audit ingestion loss

Owner: Security operator. Treat as Critical. Prevent new TradeIntent progression, verify
PostgreSQL availability and audit role permissions, preserve evidence, and restore
ingestion before re-enabling workflows.

## Telemetry loss

Owner: Platform operator. Confirm collector and Prometheus targets, preserve local logs,
and restore visibility. Escalate to Critical if audit visibility is also lost.

## Agent failures

Owner: Trading operator. Disable the affected agent scope, inspect correlation IDs and
tool outcomes, and do not retry actions that could duplicate brokerage effects.

## Latency

Owner: Platform operator. Identify the service/version and queue state, then reduce load
or roll back the affected release.

## Queue backlog

Owner: Trading operator. Pause new submissions, verify consumers and policy controls,
and drain only after duplicate-action safeguards are confirmed.

## Alert delivery failure

Owner: Platform operator. Inspect `fm_alert_delivery_attempts_total` and the redacted delivery
audit events, verify the provider and protected secret availability, and exercise the alternate
channel. Keep unsafe workflows disabled if Critical alerts cannot reach either operator path.

### Amazon SNS checks

1. Confirm the runtime has matching `AWS_REGION` and `ALERT_SMS_TOPIC_ARN` values, the protected
   `ALERT_SMS_RECIPIENT`, and the registered `ALERT_SMS_ORIGINATION_NUMBER`; do not print their
   values.
2. Confirm the workload role has only the policy in
   `infra/aws/alert-router-sns-policy.json` and no long-lived AWS access key is configured.
3. Confirm the SMS account is out of the sandbox for production, the toll-free registration is
   active, and the regional SMS spend quota has not been exhausted.
4. Use the redacted audit receipt to locate the SNS `MessageId` and check the AWS delivery-status
   logs. A `MessageId` proves provider acceptance, not handset delivery.
5. Keep the email path active while SNS is impaired. For a Critical alert, treat either missing
   channel as degraded operations even when the other channel succeeds.
