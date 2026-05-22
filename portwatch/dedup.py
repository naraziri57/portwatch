"""Event deduplication: suppress repeated identical events within a time window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


# Key: (kind, proto, port, process)
_EventKey = Tuple[str, str, int, Optional[str]]


@dataclass
class DedupWindow:
    """Tracks seen events and suppresses duplicates within a rolling window."""

    window_seconds: float = 300.0
    _seen: Dict[_EventKey, float] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

    def _key(self, event) -> _EventKey:
        entry = event.entry
        return (event.kind, entry.proto, entry.port, entry.process)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.window_seconds
        expired = [k for k, ts in self._seen.items() if ts < cutoff]
        for k in expired:
            del self._seen[k]

    def is_duplicate(self, event) -> bool:
        """Return True if this event was already seen within the window."""
        now = time.monotonic()
        self._evict_expired(now)
        key = self._key(event)
        return key in self._seen

    def record(self, event) -> None:
        """Mark an event as seen at the current time."""
        now = time.monotonic()
        self._evict_expired(now)
        key = self._key(event)
        self._seen[key] = now

    def filter_events(self, events) -> list:
        """Return only events that are not duplicates, recording each one."""
        result = []
        for ev in events:
            if not self.is_duplicate(ev):
                self.record(ev)
                result.append(ev)
        return result

    def clear(self) -> None:
        """Reset the dedup window."""
        self._seen.clear()

    @property
    def size(self) -> int:
        """Number of currently tracked event keys."""
        return len(self._seen)
