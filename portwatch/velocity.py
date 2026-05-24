"""Track the rate of port change events over time (open/close velocity)."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

from portwatch.alerter import ChangeEvent


@dataclass
class VelocityStats:
    port: int
    proto: str
    window_seconds: float
    _timestamps: Deque[float] = field(default_factory=deque, repr=False)

    def record(self, ts: Optional[float] = None) -> None:
        now = ts if ts is not None else time.time()
        self._timestamps.append(now)
        self._evict(now)

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def rate(self, now: Optional[float] = None) -> float:
        """Events per second within the current window."""
        ts = now if now is not None else time.time()
        self._evict(ts)
        if self.window_seconds <= 0:
            return 0.0
        return len(self._timestamps) / self.window_seconds

    def count(self, now: Optional[float] = None) -> int:
        ts = now if now is not None else time.time()
        self._evict(ts)
        return len(self._timestamps)

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "window_seconds": self.window_seconds,
            "event_count": self.count(),
            "rate_per_second": round(self.rate(), 4),
        }


class VelocityTracker:
    """Maintain per-port velocity stats across a sliding time window."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.window_seconds = window_seconds
        self._stats: Dict[str, VelocityStats] = {}

    def _key(self, port: int, proto: str) -> str:
        return f"{proto}:{port}"

    def record_event(self, event: ChangeEvent, ts: Optional[float] = None) -> None:
        k = self._key(event.entry.port, event.entry.proto)
        if k not in self._stats:
            self._stats[k] = VelocityStats(
                port=event.entry.port,
                proto=event.entry.proto,
                window_seconds=self.window_seconds,
            )
        self._stats[k].record(ts)

    def get(self, port: int, proto: str) -> Optional[VelocityStats]:
        return self._stats.get(self._key(port, proto))

    def all_stats(self) -> list:
        return [s.to_dict() for s in self._stats.values()]

    def hot_ports(self, threshold: float = 0.1) -> list:
        """Return stats for ports whose rate exceeds threshold events/sec."""
        return [s.to_dict() for s in self._stats.values() if s.rate() >= threshold]
