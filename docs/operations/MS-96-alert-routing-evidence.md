# MS-96 alert-routing acceptance evidence

Decision: High alerts route to email; Critical alerts route to email and SMS. High email failure
falls back to SMS after three attempts. Critical channels are attempted independently.

Automated evidence is produced by `tests/test_alert_routing.py` through the authoritative
`make validate` path. The test sends representative High and Critical alerts through the router,
captures independent channel receipts, forces repeated email failure, verifies SMS fallback, and
checks delivery-failure metrics and redacted audit records.

Production activation evidence remains pending until the owner supplies the destination email,
mobile number, and provider credentials through the protected PROD secret store. No destination
or credential may be committed to this file.
