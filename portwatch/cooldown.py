"""Cooldown tracker — suppresses repeated alerts for a port until a quiet period elapses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


@dataclass
class CooldownPolicy:
    quiet_period: int = 300  # seconds before a port is eligible for re-alerting
    max_suppressions: int = 10  # max times a single port can be suppressed before forced re-alert

    def __post_init__(self) -> None:
        if self.quiet_period <= 0:
            raise ValueError("quiet_period must be positive")
        if self.max_suppressions <= 0:
            raise ValueError("max_suppressions must be positive")


@dataclass
class _CooldownEntry:
    last_alerted: datetime
    suppression_count: int = 0


@dataclass
class CooldownTracker:
    policy: CooldownPolicy = field(default_factory=CooldownPolicy)
    _state: Dict[Tuple[int, str], _CooldownEntry] = field(default_factory=dict, repr=False)

    def _key(self, port: int, proto: str) -> Tuple[int, str]:
        return (port, proto.lower())

    def is_suppressed(self, port: int, proto: str, now: Optional[datetime] = None) -> bool:
        """Return True if this port/proto alert should be suppressed."""
        now = now or datetime.utcnow()
        key = self._key(port, proto)
        entry = self._state.get(key)
        if entry is None:
            return False
        elapsed = (now - entry.last_alerted).total_seconds()
        if entry.suppression_count >= self.policy.max_suppressions:
            return False  # force re-alert after max suppressions
        return elapsed < self.policy.quiet_period

    def record_alert(self, port: int, proto: str, now: Optional[datetime] = None) -> None:
        """Record that an alert was sent for this port/proto."""
        now = now or datetime.utcnow()
        key = self._key(port, proto)
        self._state[key] = _CooldownEntry(last_alerted=now, suppression_count=0)

    def record_suppression(self, port: int, proto: str) -> None:
        """Increment suppression count for a port/proto pair."""
        key = self._key(port, proto)
        entry = self._state.get(key)
        if entry is not None:
            entry.suppression_count += 1

    def reset(self, port: int, proto: str) -> None:
        """Clear cooldown state for a specific port/proto."""
        self._state.pop(self._key(port, proto), None)

    def reset_all(self) -> None:
        """Clear all cooldown state."""
        self._state.clear()

    def suppression_count(self, port: int, proto: str) -> int:
        entry = self._state.get(self._key(port, proto))
        return entry.suppression_count if entry else 0
