"""Alert throttling to suppress repeated notifications for the same port change."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

# Key: (proto, port, change_type)
_ThrottleKey = Tuple[str, int, str]


@dataclass
class ThrottleState:
    first_seen: float
    last_seen: float
    count: int = 1


@dataclass
class Throttler:
    """Suppress duplicate alerts within a cooldown window."""

    cooldown_seconds: float = 300.0
    _state: Dict[_ThrottleKey, ThrottleState] = field(default_factory=dict, init=False)

    def should_send(self, proto: str, port: int, change_type: str) -> bool:
        """Return True if the alert should be sent (not throttled)."""
        key: _ThrottleKey = (proto, port, change_type)
        now = time.monotonic()

        if key not in self._state:
            self._state[key] = ThrottleState(first_seen=now, last_seen=now)
            return True

        entry = self._state[key]
        elapsed = now - entry.last_seen

        if elapsed >= self.cooldown_seconds:
            # Cooldown expired — reset and allow
            self._state[key] = ThrottleState(first_seen=now, last_seen=now)
            return True

        # Still within cooldown window — suppress
        entry.last_seen = now
        entry.count += 1
        return False

    def get_suppressed_count(self, proto: str, port: int, change_type: str) -> int:
        """Return how many times an alert has been suppressed for this key."""
        key: _ThrottleKey = (proto, port, change_type)
        state = self._state.get(key)
        return state.count - 1 if state else 0

    def clear(self, proto: Optional[str] = None, port: Optional[int] = None,
              change_type: Optional[str] = None) -> None:
        """Clear throttle state, optionally filtered by key components."""
        if proto is None and port is None and change_type is None:
            self._state.clear()
            return
        to_remove = [
            k for k in self._state
            if (proto is None or k[0] == proto)
            and (port is None or k[1] == port)
            and (change_type is None or k[2] == change_type)
        ]
        for k in to_remove:
            del self._state[k]
