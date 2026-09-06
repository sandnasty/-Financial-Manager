# MS-96 Amazon SNS production activation

This checklist completes the owner-controlled AWS work that cannot be performed from source code.
Do not paste telephone numbers, verification codes, AWS credentials, or Gmail app passwords into
issues, pull requests, logs, or chat.

## One-time AWS setup

1. Use AWS Region `us-east-1` for the registered origination identity and create the dedicated
   Financial Manager SNS topic in the same Region. The application rejects a topic ARN from a
   different Region.
2. In AWS End User Messaging SMS, request a US toll-free number and submit its registration for
   the Financial Manager transactional operational-alert use case.
3. While the account is in the SNS SMS sandbox, add and verify only the owner's destination phone
   number. Request production access after the test route is successful.
4. Set a conservative account monthly SMS spending limit. The application additionally caps each
   publish at `ALERT_SMS_MAX_PRICE_USD`, initially USD 0.05.
5. Enable SMS delivery-status logging to CloudWatch so the SNS provider receipt can be reconciled
   with carrier and handset delivery outcomes.
6. Subscribe only the protected owner destination to the dedicated topic.
7. Render `ALERT_SMS_TOPIC_ARN` into `infra/aws/alert-router-sns-policy.json` and assign the
   resulting least-privilege policy to the dedicated alert-router workload role. Do not create a
   long-lived IAM user access key.

## Protected production values

Configure these only in the protected PROD runtime environment:

- `ALERT_SMS_TOPIC_ARN`: dedicated topic ARN in the selected Region.
- `ALERT_SMS_RECIPIENT`: owner destination in E.164 format.
- `ALERT_SMS_ORIGINATION_NUMBER`: registered AWS toll-free number in E.164 format.
- `AWS_REGION`: `us-east-1`.
- `ALERT_SMS_MAX_PRICE_USD`: `0.05` initially.

The AWS SDK obtains short-lived credentials from the alert-router workload role. There is no
`ALERT_SMS_CREDENTIAL` secret.

## Acceptance exercise

1. Send a High test alert and confirm email delivery without SMS.
2. Simulate three email-provider failures for a High alert and confirm one SMS fallback delivery.
3. Send a Critical test alert and independently confirm both Gmail and SMS delivery.
4. Preserve the redacted audit events, SNS `MessageId` receipts, delivery-status outcomes,
   timestamps, deployed version, and operator acknowledgement in the MS-96 evidence record.
5. Preserve the external activation evidence in the dedicated AWS activation issue before live
   trading is enabled.
