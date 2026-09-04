# Financial Manager

Secure, explainable trading decision-support and execution platform progressing from research through paper trading, human-approved live trading, and controlled automation.

## Build and test

The supported developer platform is Windows + WSL2 with Linux-style tools and Docker Desktop's WSL2 backend. From the repository root:

```sh
make doctor
make validate
```

`make validate` is the authoritative local/CI entry point: it verifies pinned inputs, formatting and lint policy, runs unit and reproducibility tests, and builds the representative service artifact. See [Deterministic local build and test](docs/development/build-and-test.md) for setup, failure behavior, and the complete command interface.
