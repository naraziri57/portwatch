"""Track port open/close frequency over time to detect noisy or flapping ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


@dataclass
class PortTrend:
    """Accumulated event counts for a single (port, proto) pair."""

    port: int
    proto: str
    opens: int = 0
    closes: int = 0
    last_seen: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_events(self) -> int:
        return self.opens + self.closes

    def is_flapping(self, threshold: int = 3) -> bool:
        """Return True when both opens and closes exceed *threshold*."""
        return self.opens >= threshold and self.closes >= threshold

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "opens": self.opens,
            "closes": self.closes,
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class TrendTracker:
    """Maintain per-port trends within a rolling time window."""

    window_minutes: int = 60
    _data: Dict[Tuple[int, str], PortTrend] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.window_minutes <= 0:
            raise ValueError("window_minutes must be positive")

    def _key(self, port: int, proto: str) -> Tuple[int, str]:
        return (port, proto.lower())

    def record_open(self, port: int, proto: str) -> None:
        key = self._key(port, proto)
        trend = self._data.setdefault(key, PortTrend(port=port, proto=proto))
        trend.opens += 1
        trend.last_seen = datetime.utcnow()

    def record_close(self, port: int, proto: str) -> None:
        key = self._key(port, proto)
        trend = self._data.setdefault(key, PortTrend(port=port, proto=proto))
        trend.closes += 1
        trend.last_seen = datetime.utcnow()

    def evict_stale(self) -> None:
        """Remove entries not updated within the rolling window."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        stale = [k for k, v in self._data.items() if v.last_seen < cutoff]
        for k in stale:
            del self._data[k]

    def flapping_ports(self, threshold: int = 3) -> List[PortTrend]:
        self.evict_stale()
        return [t for t in self._data.values() if t.is_flapping(threshold)]

    def all_trends(self) -> List[PortTrend]:
        self.evict_stale()
        return list(self._data.values())

    def reset(self) -> None:
        self._data.clear()
