"""Fail-closed operational controls for autonomous actions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Callable

AuditSink = Callable[[dict[str, str]], None]


class AuthorizationError(PermissionError):
    pass


class ActionDisabled(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ControlState:
    global_enabled: bool = True
    trade_intent_enabled: bool = True
    disabled_agents: frozenset[str] = frozenset()
    autonomy_level: str = "recommendation"


class OperationalControls:
    def __init__(self, audit: AuditSink) -> None:
        self.state = ControlState()
        self.audit = audit

    def set_state(self, *, operator_role: str, confirmation: str,
                  reason: str, **changes: object) -> ControlState:
        if operator_role != "authorized-operator":
            raise AuthorizationError("ordinary agents cannot change operational controls")
        if confirmation != "CONFIRM":
            raise AuthorizationError("explicit operator confirmation is required")
        previous = self.state
        self.state = replace(self.state, **changes)
        self.audit({"action": "operational-control.changed", "actor_type": "human",
                    "occurred_at": datetime.now(UTC).isoformat(), "reason": reason,
                    "previous": repr(previous), "current": repr(self.state)})
        return self.state

    def require_action(self, action: str, agent: str | None = None) -> None:
        if not self.state.global_enabled:
            raise ActionDisabled("global autonomous actions are disabled")
        if agent and agent in self.state.disabled_agents:
            raise ActionDisabled(f"agent {agent} is disabled")
        if action == "trade-intent.submit" and not self.state.trade_intent_enabled:
            raise ActionDisabled("new TradeIntent submission is disabled")
