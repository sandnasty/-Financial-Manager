"""Auditable multi-channel delivery for High and Critical alerts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any, Callable, Protocol

from financial_manager.audit import redact
from financial_manager.observability import Metrics

AuditSink = Callable[[dict[str, Any]], None]
Sleep = Callable[[float], None]


class AlertChannel(Protocol):
    def send(self, alert: "OperationalAlert") -> str: ...


class AlertDeliveryFailed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OperationalAlert:
    fingerprint: str
    name: str
    severity: str
    owner: str
    summary: str
    runbook_url: str
    status: str = "firing"


@dataclass(frozen=True, slots=True)
class Route:
    channels: tuple[str, ...]
    fallback_channels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    routes: dict[str, Route]
    max_attempts: int
    retry_backoff_seconds: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DeliveryReport:
    fingerprint: str
    delivered: dict[str, str]
    failed: dict[str, str]


def load_routing_policy(path: Path) -> RoutingPolicy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    routes = {
        severity: Route(tuple(value["channels"]), tuple(value["fallback_channels"]))
        for severity, value in raw["routes"].items()
    }
    max_attempts = int(raw["delivery"]["max_attempts"])
    backoff = tuple(map(int, raw["delivery"]["retry_backoff_seconds"]))
    if set(routes) != {"high", "critical"} or max_attempts < 1:
        raise ValueError("routing policy must define High and Critical delivery")
    if len(backoff) != max_attempts - 1:
        raise ValueError("one retry backoff is required between delivery attempts")
    return RoutingPolicy(routes, max_attempts, backoff)


class AlertRouter:
    def __init__(
        self,
        *,
        policy: RoutingPolicy,
        channels: dict[str, AlertChannel],
        audit: AuditSink,
        metrics: Metrics,
        wait: Sleep = sleep,
    ) -> None:
        self.policy = policy
        self.channels = channels
        self.audit = audit
        self.metrics = metrics
        self.wait = wait

    def _deliver(self, channel_name: str, alert: OperationalAlert) -> tuple[str | None, str | None]:
        channel = self.channels.get(channel_name)
        if channel is None:
            return None, "channel-not-configured"
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                receipt = channel.send(alert)
            except Exception as exc:  # provider adapters normalize errors at this boundary
                reason = type(exc).__name__
                self.metrics.increment(
                    "fm_alert_delivery_attempts_total",
                    channel=channel_name,
                    result="failure",
                )
                self.audit(
                    {
                        "action": "alert.delivery",
                        "target_id": alert.fingerprint,
                        "channel": channel_name,
                        "attempt": str(attempt),
                        "result": "failure",
                        "reason": reason,
                        "occurred_at": datetime.now(UTC).isoformat(),
                    }
                )
                if attempt < self.policy.max_attempts:
                    self.wait(self.policy.retry_backoff_seconds[attempt - 1])
                continue
            self.metrics.increment(
                "fm_alert_delivery_attempts_total", channel=channel_name, result="success"
            )
            self.audit(
                {
                    "action": "alert.delivery",
                    "target_id": alert.fingerprint,
                    "channel": channel_name,
                    "attempt": str(attempt),
                    "result": "success",
                    "receipt": receipt,
                    "occurred_at": datetime.now(UTC).isoformat(),
                }
            )
            return receipt, None
        self.metrics.increment("fm_alert_delivery_failures_total", channel=channel_name)
        return None, reason

    def route(self, alert: OperationalAlert) -> DeliveryReport:
        severity = alert.severity.lower()
        route = self.policy.routes.get(severity)
        if route is None:
            raise AlertDeliveryFailed("only High and Critical alerts use the production route")
        safe_alert = OperationalAlert(**redact(asdict(alert)))
        delivered: dict[str, str] = {}
        failed: dict[str, str] = {}
        for channel_name in route.channels:
            receipt, failure = self._deliver(channel_name, safe_alert)
            if receipt:
                delivered[channel_name] = receipt
            else:
                failed[channel_name] = failure or "delivery-failed"
        if not delivered:
            for channel_name in route.fallback_channels:
                receipt, failure = self._deliver(channel_name, safe_alert)
                if receipt:
                    delivered[channel_name] = receipt
                    break
                failed[channel_name] = failure or "delivery-failed"
        if not delivered:
            raise AlertDeliveryFailed("all configured production alert channels failed")
        return DeliveryReport(alert.fingerprint, delivered, failed)
