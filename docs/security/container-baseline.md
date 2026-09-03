# Financial Manager Container Security Baseline

Status: MS-59 implementation baseline

## Scope

This baseline applies to Financial Manager application services and agents unless an explicitly approved exception is documented through the ADR process.

## Required controls

- OCI-compatible container images.
- Docker-compatible local and CI workflow.
- Compose for early multi-service integration.
- Kubernetes is not required for M1.
- Application processes run as a fixed non-root UID/GID. Rootless host runtime operation is preferred where supported.
- Root filesystem is read-only by default.
- Writable areas are explicit, minimal, and bounded; the baseline currently permits only a bounded tmpfs at `/tmp`.
- All Linux capabilities are dropped by default.
- `no-new-privileges` is required.
- Privileged containers are prohibited.
- Host runtime sockets, host namespaces, and host devices are not mounted or exposed by default.
- CPU, memory, and PID limits are defined in Compose.
- Images use a minimal approved base with a fixed patch-level version. Digest pinning may be added by the supply-chain hardening work in E03, but version drift is not permitted silently.
- Docker's default seccomp profile remains enabled. On Linux hosts with AppArmor enabled, the runtime default AppArmor profile remains required unless a stricter service-specific profile is introduced.
- Health checks are required for long-running services.
- Failure to satisfy a required security control is fail-closed; exceptions require an ADR and owner approval.
- No broker credential, signing material, or production secret is baked into images or committed to the repository.

## Baseline verification

Run:

```sh
sh tests/security/test_container_baseline.sh
```

The negative test verifies that the baseline service:

1. does not run as root;
2. cannot write to the read-only root filesystem;
3. has no effective Linux capabilities;
4. cannot see the host Docker/OCI runtime socket;
5. cannot see prohibited host devices such as `/dev/kvm` or `/dev/mem`; and
6. can write only to the explicitly scoped `/tmp` tmpfs used by the baseline.

## Host/runtime requirements

The baseline is designed for Docker-compatible OCI runtimes. Rootless Docker or an equivalent rootless OCI runtime should be used where the host supports it. Where the host cannot operate the daemon/root runtime itself without privilege, application containers must still run non-root and retain every in-container control defined here.

## Exceptions

Any service needing additional capabilities, writable storage, host integration, external networking, or a weaker security profile must document:

- the exact requested exception;
- why the baseline is insufficient;
- the threat/risk introduced;
- compensating controls;
- verification evidence; and
- explicit owner approval.

The exception must be captured in an ADR before use in a live environment.
