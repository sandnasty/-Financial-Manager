# ADR-0005: Local notification setup wizard

- Status: Accepted
- Date: 2026-09-05
- Decision owner: Project owner
- Linear issue: MS-97
- Requirement: FM-UX-001

## Context

Financial Manager needs per-installation email and SMS destinations without placing account
information in its public repository. Operators also need to change those choices without editing
source files. The setup flow must remain usable before the platform audit database or deployment
secret store is available.

## Decision

The application runs a required notification wizard when no valid local settings file exists.
The same wizard is available later through **Settings > Notifications**. It supports email, SMS,
both channels, or an explicitly confirmed disabled state.

The wizard stores only non-credential configuration: recipient addresses, telephone numbers, AWS
region, AWS profile name, SNS topic ARN, registered origination number, and the per-message price
cap. The topic ARN Region must match the selected AWS Region. It never
collects Gmail passwords or app passwords, AWS access keys, secret keys, session tokens, SSO
codes, or verification codes. Amazon SNS authentication continues to use the AWS SDK credential
chain; local installations should use AWS SSO or another short-lived profile.

Settings use the operating system's per-user configuration folder rather than the source checkout.
Writes are atomic. On POSIX systems the directory and files are restricted to the owner. A masked
review appears before save. Invalid or unreadable configuration fails closed and starts recovery
setup rather than normal operation.

Each successful save emits only the actor, result, timestamp, and names of changed fields. The
standalone application writes that redacted event to an owner-readable local JSON Lines file. A
deployed service may inject the canonical audit sink defined by ADR-0002.

## Consequences

- A public clone contains no operator email address, telephone number, AWS account identifier, or
  AWS account credential.
- Each installation can have independent notification settings.
- Copying the source repository does not copy the OS user configuration folder.
- Backing up or sharing the user configuration folder can still disclose destinations, so it must
  be treated as private local data.
- SMTP/Gmail authorization and AWS SSO login remain provider-controlled activation steps; the
  wizard deliberately does not capture those credentials.

## Verification

- `financial_manager/app.py`
- `financial_manager/notification_settings.py`
- `tests/test_notification_setup.py`
- `docs/operations/notification-setup.md`

## Impacted requirements and issues

- FM-UX-001
- MS-97
- MS-96
- ADR-0002
- ADR-0004
