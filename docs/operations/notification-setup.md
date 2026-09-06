# Notification setup

## Start or reopen setup

Run `make run`. On the first launch, Financial Manager requires the notification wizard before it
opens the main menu. To change the configuration later, select **Settings**, then
**Notifications**.

The wizard supports:

- email alerts, with one recipient address;
- SMS alerts through Amazon SNS;
- both channels; or
- an explicitly confirmed disabled state.

Values are reviewed in masked form before the file is saved. Canceling first-run setup prevents
normal operation. Canceling a later edit leaves the previous configuration unchanged.

## Local files

The default settings file is outside the Git checkout:

- Linux/WSL: `$XDG_CONFIG_HOME/financial-manager/settings.json`, or
  `$HOME/.config/financial-manager/settings.json` when `XDG_CONFIG_HOME` is unset;
- Windows: `%APPDATA%\Financial Manager\settings.json`.

The redacted local change trail is `settings-audit.jsonl` in the same folder. POSIX permissions are
`0700` for the folder and `0600` for both files. These files are private local data: do not attach
them to issues, commit them, or copy them into a shared directory. Root-level fallback filenames
are also ignored by Git.

For an isolated test, choose a temporary path explicitly:

```sh
python -m financial_manager.app --settings /tmp/fm-test/settings.json
```

## Amazon SNS authentication

Enter the AWS Region, SNS topic ARN, and the name of a locally configured AWS profile. The topic
ARN must be in the selected Region. The default is `us-east-1`, but the wizard accepts any valid
regional SNS topic and rejects a Region/ARN mismatch. Use AWS SSO so the SDK can obtain short-lived
credentials, for example:

```sh
aws configure sso --profile financial-manager
aws sso login --profile financial-manager
```

Then enter `financial-manager` as the profile name in the wizard. Never enter or store AWS access
keys in this application. The wizard also collects the destination and registered origination
numbers in E.164 format and a maximum per-message USD price. The alert adapter publishes to the
topic; AWS delivers to the phone numbers subscribed to that topic. Complete the account-side controls in
[MS-96 Amazon SNS production activation](MS-96-aws-sns-activation.md).

## Email boundary

The wizard stores the email alert destination only. It does not store a Gmail password, app
password, OAuth refresh token, or mailbox verification code. Provider authorization for actual
Gmail delivery must use a protected runtime integration when that adapter is activated.

## Recovery

If the settings file is missing, malformed, has unsupported fields, or fails validation, Financial
Manager does not continue with partially trusted values. It opens required recovery setup and
atomically replaces the file only after a valid, confirmed configuration is entered.
