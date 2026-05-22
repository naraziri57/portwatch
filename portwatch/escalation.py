"""Escalation policy: re-alert if an issue persists beyond a threshold."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class EscalationPolicy:
    """Re-alert after *escalate_after* seconds if the same event is still active."""

    escalate_after: float = 300.0  # seconds until first escalation
    max_escalations: int = 3       # stop escalating after this many repeats

    def __post_init__(self) -> None:
        if self.escalate_after <= 0:
            raise ValueError("escalate_after must be positive")
        if self.max_escalations < 1:
            raise ValueError("max_escalations must be >= 1")


@dataclass
class _EscalationEntry:
    first_seen: float
    last_escalated: float
    count: int = 0


@dataclass
class EscalationTracker:
    """Tracks open issues and decides when to escalate."""

    policy: EscalationPolicy = field(default_factory=EscalationPolicy)
    _state: Dict[str, _EscalationEntry] = field(default_factory=dict, init=False, repr=False)

    def _key(self, proto: str, port: int) -> str:
        return f"{proto}:{port}"

    def open(self, proto: str, port: int) -> None:
        """Mark an issue as currently open (call on each scan cycle)."""
        k = self._key(proto, port)
        if k not in self._state:
            now = time.time()
            self._state[k] = _EscalationEntry(first_seen=now, last_escalated=now)

    def close(self, proto: str, port: int) -> None:
        """Mark an issue as resolved."""
        self._state.pop(self._key(proto, port), None)

    def due(self, proto: str, port: int) -> bool:
        """Return True if this issue is due for an escalation alert."""
        k = self._key(proto, port)
        entry = self._state.get(k)
        if entry is None:
            return False
        if entry.count >= self.policy.max_escalations:
            return False
        elapsed = time.time() - entry.last_escalated
        return elapsed >= self.policy.escalate_after

    def mark_escalated(self, proto: str, port: int) -> int:
        """Record that an escalation was sent; returns new escalation count."""
        k = self._key(proto, port)
        entry = self._state.get(k)
        if entry is None:
            raise KeyError(f"No open issue for {k}")
        entry.count += 1
        entry.last_escalated = time.time()
        return entry.count

    def open_keys(self):
        return list(self._state.keys())
