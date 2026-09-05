# ADR-0003 — Observability Stack and Correlation

Status: Accepted
Date: 2026-09-05
Decision owner: Owner/Human
Related: Linear MS-67, E03-05

## Decision

Use OpenTelemetry as the vendor-neutral collection boundary, Prometheus for
metrics, and Grafana for operator views. Services emit structured JSON logs and
propagate a correlation ID and trace ID through API, agent, TradeIntent, audit,
and brokerage boundaries. Initial telemetry retention is 90 days.

The common identity fields are service, semantic version/build SHA, environment,
severity, timestamp, correlation ID, and trace ID. Secret, credential, token,
authorization, cookie, password, and account-number fields are redacted before
emission. Agent metrics record counts, outcomes, and duration, never prompts,
secret values, or prohibited financial content.

## Consequences

The M1 service has a dependency-free instrumentation facade and Prometheus text
endpoint while preserving the selected OpenTelemetry export boundary. Later
services must use the same semantic fields and context propagation contract.

## Verification

- `financial_manager/observability.py`
- `infra/observability/otel-collector.yaml`
- `infra/observability/prometheus.yaml`
- `tests/test_observability.py`
