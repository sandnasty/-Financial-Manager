# Financial Manager

Secure, explainable trading decision-support and execution platform progressing from research through paper trading, human-approved live trading, and controlled automation.

## Build and test

The supported developer platform is Windows + WSL2 with Linux-style tools and Docker Desktop's WSL2 backend. Python 3.14.7 is the authoritative pinned runtime. From the repository root:

```sh
make doctor
make validate
```

`make validate` is the authoritative local/CI entry point: it verifies pinned inputs, formatting and lint policy, runs unit and reproducibility tests, and builds the representative service artifact. See [Deterministic local build and test](docs/development/build-and-test.md) for setup, failure behavior, and the complete command interface.

## First-run notification setup

Run the application shell with:

```sh
make run
```

The first launch opens a notification wizard before the main menu. It can enable email, SMS, or
both and stores the non-credential settings in the operating system's user configuration folder,
outside the repository. Return to the wizard later through **Settings > Notifications**. See
[Notification setup](docs/operations/notification-setup.md) for AWS SSO and local-file details.
