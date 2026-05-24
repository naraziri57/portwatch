"""Lockout module: temporarily block alerting for specific ports after repeated noise."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class LockoutPolicy:
    """Configuration for the lockout mechanism."""
    trigger_count: int = 5       # events within window to trigger lockout
    window_seconds: float = 60.0 # sliding window size
    lockout_seconds: float = 300.0 # how long to lock out the port

    def __post_init__(self) -> None:
        if self.trigger_count < 1:
            raise ValueError("trigger_count must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.lockout_seconds <= 0:
            raise ValueError("lockout_seconds must be positive")


@dataclass
class _PortState:
    timestamps: list = field(default_factory=list)  # recent event times
    locked_until: Optional[float] = None


class LockoutTracker:
    """Tracks per-port event frequency and enforces lockout periods."""

    def __init__(self, policy: Optional[LockoutPolicy] = None) -> None:
        self._policy = policy or LockoutPolicy()
        self._states: Dict[Tuple[int, str], _PortState] = {}

    def _key(self, port: int, proto: str) -> Tuple[int, str]:
        return (port, proto.lower())

    def _state(self, key: Tuple[int, str]) -> _PortState:
        if key not in self._states:
            self._states[key] = _PortState()
        return self._states[key]

    def is_locked(self, port: int, proto: str) -> bool:
        """Return True if the port is currently locked out."""
        key = self._key(port, proto)
        state = self._state(key)
        if state.locked_until is None:
            return False
        if time.monotonic() < state.locked_until:
            return True
        # lockout expired — clear it
        state.locked_until = None
        state.timestamps.clear()
        return False

    def record_event(self, port: int, proto: str) -> bool:
        """Record an event; returns True if a new lockout was triggered."""
        if self.is_locked(port, proto):
            return False
        key = self._key(port, proto)
        state = self._state(key)
        now = time.monotonic()
        cutoff = now - self._policy.window_seconds
        state.timestamps = [t for t in state.timestamps if t >= cutoff]
        state.timestamps.append(now)
        if len(state.timestamps) >= self._policy.trigger_count:
            state.locked_until = now + self._policy.lockout_seconds
            state.timestamps.clear()
            return True
        return False

    def locked_ports(self) -> list:
        """Return list of (port, proto) pairs currently locked out."""
        now = time.monotonic()
        return [
            k for k, s in self._states.items()
            if s.locked_until is not None and now < s.locked_until
        ]

    def clear(self, port: int, proto: str) -> None:
        """Manually clear lockout and history for a port."""
        key = self._key(port, proto)
        self._states.pop(key, None)
