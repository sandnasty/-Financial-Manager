# ADR-0001 — Initial Container Runtime Baseline

Status: Accepted
Date: 2026-09-02
Decision owner: Owner/Human
Related: Linear MS-59, E02 Security & Container Platform

## Context

Financial Manager requires a reproducible, least-privilege container foundation before market-data, agent, risk, approval, or brokerage services are implemented. The platform must support local development and CI without prematurely adding orchestration complexity, while preserving a path to production-grade orchestration later.

## Decision

Use OCI-compatible containers with a Docker-compatible local and CI workflow. Use Compose for early multi-service integration. Do not make Kubernetes a dependency of the M1 Secure Platform Skeleton.

All application containers must default to fixed non-root identities, read-only root filesystems, explicitly scoped writable mounts, dropped Linux capabilities, no-new-privileges, no privileged mode, no host runtime socket access, no host namespace/device access without an approved exception, bounded resources, health checks, and default runtime seccomp/AppArmor-equivalent confinement.

Rootless host runtime operation is preferred where supported. A host that cannot run the daemon/root runtime rootlessly does not relax the requirement that application processes run non-root with the in-container controls above.

## Alternatives considered

1. Kubernetes immediately — rejected for M1 because it adds orchestration and operational complexity before the service architecture requires it.
2. Uncontainerized local services — rejected because it weakens reproducibility and the planned trust boundaries.
3. Privileged development containers — rejected because development convenience must not establish an unsafe baseline that can drift into paper/live environments.

## Security/risk impact

The decision reduces default privilege, host exposure, writable attack surface, and accidental cross-service trust. Residual risk remains in the host container runtime and kernel; later production deployment must address host/orchestrator hardening and the SR-04 live-activation blocker from the E02 threat model.

## Data/model impact

None directly. Future data/model services inherit the same container baseline and must request explicit exceptions for storage or device requirements.

## Operational impact

Developers and CI need a Docker-compatible OCI runtime and Compose. Linux security profiles use the runtime defaults unless a stricter service-specific profile is approved. Portability to Kubernetes or another orchestrator is preserved by keeping security requirements independent of Compose syntax.

## Consequences

Positive:
- simple local/CI startup;
- reproducible least-privilege defaults;
- reduced chance of privileged-development drift;
- clear migration path to later orchestration.

Tradeoffs:
- Compose is not the intended final production orchestrator;
- some host-level rootless behavior is platform-dependent;
- service-specific exceptions may require future ADRs.

## Impacted requirements/issues

- FM-SEC-003
- FM-SEC-004
- FM-SEC-011
- MS-59 / E02-03
- MS-60 / E02-04
- MS-61 / E02-05
- MS-64 / E03-02
- MS-65 / E03-03

## Verification/evidence

- `infra/container/Dockerfile`
- `compose.yaml`
- `docs/security/container-baseline.md`
- `tests/security/test_container_baseline.sh`
- `.github/workflows/ms-59-container-baseline.yml`

## Approval

Owner approved the OCI/Docker-compatible + Compose approach on September 2, 2026 before MS-59 repository implementation began.

## Supersession

A later production orchestrator decision may supersede the orchestration portion of this ADR, but must preserve or strengthen the security invariants unless the owner explicitly accepts a documented exception.
