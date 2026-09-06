# MS-96 alert-routing acceptance evidence

Provider activation details: [Amazon SNS production activation](MS-96-aws-sns-activation.md).

Decision: High alerts route to email; Critical alerts route to email and SMS. High email failure
falls back to SMS after three attempts. Critical channels are attempted independently.

Automated evidence is produced by `tests/test_alert_routing.py` through the authoritative
`make validate` path. The test sends representative High and Critical alerts through the router,
captures independent channel receipts, forces repeated email failure, verifies SMS fallback, and
checks delivery-failure metrics and redacted audit records.

The Gmail sender and recipient path has been verified. Production SMS activation remains pending
until the owner supplies a dedicated same-Region topic through protected runtime configuration,
subscribes the protected destination, and the registered AWS toll-free number becomes active. No
topic ARN, destination, account identifier, or credential may be committed to this file.
