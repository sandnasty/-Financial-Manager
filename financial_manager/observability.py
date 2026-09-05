"""Dependency-free observability facade for logs, metrics, and trace context."""

from __future__ import annotations

import json
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from financial_manager.audit import redact

_context: ContextVar["TraceContext | None"] = ContextVar("trace_context", default=None)


@dataclass(frozen=True, slots=True)
class TraceContext:
    correlation_id: str
    trace_id: str

    @classmethod
    def new(cls, correlation_id: str | None = None) -> "TraceContext":
        return cls(correlation_id or str(uuid4()), uuid4().hex)


def set_trace_context(context: TraceContext) -> None:
    _context.set(context)


class JsonFormatter(logging.Formatter):
    """Emit one redacted, machine-readable event per line."""

    def __init__(self, service: str, version: str, environment: str) -> None:
        super().__init__()
        self.identity = {
            "service": service,
            "version": version,
            "environment": environment,
        }

    def format(self, record: logging.LogRecord) -> str:
        context = _context.get()
        event = {
            "timestamp_unix_ns": time.time_ns(),
            "severity": record.levelname,
            "message": record.getMessage(),
            **self.identity,
            "correlation_id": context.correlation_id if context else None,
            "trace_id": context.trace_id if context else None,
            "attributes": redact(getattr(record, "attributes", {})),
        }
        return json.dumps(event, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class Metrics:
    """Small Prometheus exposition registry used by the initial service."""

    counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=dict
    )
    gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=dict
    )

    def increment(self, name: str, value: float = 1, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        self.counters[key] = self.counters.get(key, 0) + value

    def gauge(self, name: str, value: float, **labels: str) -> None:
        self.gauges[(name, tuple(sorted(labels.items())))] = value

    def render(self) -> str:
        lines: list[str] = []
        for source in (self.counters, self.gauges):
            for (name, labels), value in sorted(source.items()):
                suffix = ""
                if labels:
                    encoded = ",".join(f'{key}="{val}"' for key, val in labels)
                    suffix = "{" + encoded + "}"
                lines.append(f"{name}{suffix} {value:g}")
        return "\n".join(lines) + "\n"


def agent_outcome(
    metrics: Metrics, agent: str, tool: str, outcome: str, duration_seconds: float
) -> None:
    """Record agent/tool results without prompts, credentials, or account data."""
    metrics.increment("fm_agent_executions_total", agent=agent, outcome=outcome)
    metrics.increment("fm_tool_calls_total", tool=tool, outcome=outcome)
    metrics.gauge("fm_agent_last_duration_seconds", duration_seconds, agent=agent)
