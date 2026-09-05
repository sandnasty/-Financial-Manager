"""Default-deny service and external network authorization."""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

AuditSink = Callable[[dict[str, str]], None]


class NetworkAccessDenied(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class ServiceNetworkPolicy:
    east_west: frozenset[str]
    egress_hosts: frozenset[str]


def load_network_policy(path: Path) -> dict[str, ServiceNetworkPolicy]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("default") != "deny":
        raise ValueError("network policy must default to deny")
    return {
        name: ServiceNetworkPolicy(
            east_west=frozenset(map(str, policy["east_west"])),
            egress_hosts=frozenset(host.lower() for host in policy["egress_hosts"]),
        )
        for name, policy in raw["services"].items()
    }


class NetworkPolicy:
    def __init__(self, policies: dict[str, ServiceNetworkPolicy], audit: AuditSink) -> None:
        self.policies = policies
        self.audit = audit

    def _record(self, service: str, kind: str, destination: str, result: str, reason: str) -> None:
        self.audit(
            {
                "action": "network.authorize",
                "actor_id": service,
                "connection_kind": kind,
                "destination": destination,
                "result": result,
                "reason": reason,
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )

    def authorize_service(self, source: str, destination: str) -> None:
        policy = self.policies.get(source)
        allowed = policy is not None and destination in policy.east_west
        self._record(source, "east-west", destination, "allowed" if allowed else "denied", "policy")
        if not allowed:
            raise NetworkAccessDenied("service-to-service connection denied")

    def authorize_egress(self, service: str, url: str) -> str:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        try:
            port = parsed.port
        except ValueError:
            port = -1
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or port not in (None, 443)
        ):
            self._record(service, "egress", host or url, "denied", "invalid-destination")
            raise NetworkAccessDenied("external destination denied")

        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            self._record(service, "egress", host, "denied", "ip-literal-denied")
            raise NetworkAccessDenied("external destination denied")

        policy = self.policies.get(service)
        allowed = policy is not None and host in policy.egress_hosts
        self._record(
            service,
            "egress",
            host,
            "allowed" if allowed else "denied",
            "exact-host-policy",
        )
        if not allowed:
            raise NetworkAccessDenied("external destination denied")
        return host
