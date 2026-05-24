"""Latency tracking for port probes."""
from __future__ import annotations

import time
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LatencyStats:
    """Tracks round-trip latency samples for a single port."""
    port: int
    proto: str
    _samples: List[float] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"port must be 1-65535, got {self.port}")
        if self.proto not in ("tcp", "udp"):
            raise ValueError(f"proto must be tcp or udp, got {self.proto!r}")

    def record(self, latency_ms: float) -> None:
        """Record a latency sample in milliseconds."""
        if latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        self._samples.append(latency_ms)

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def mean_ms(self) -> Optional[float]:
        if not self._samples:
            return None
        return statistics.mean(self._samples)

    @property
    def min_ms(self) -> Optional[float]:
        return min(self._samples) if self._samples else None

    @property
    def max_ms(self) -> Optional[float]:
        return max(self._samples) if self._samples else None

    @property
    def stdev_ms(self) -> Optional[float]:
        if len(self._samples) < 2:
            return None
        return statistics.stdev(self._samples)

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "sample_count": self.sample_count,
            "mean_ms": self.mean_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "stdev_ms": self.stdev_ms,
        }


class LatencyTracker:
    """Manages latency stats across multiple ports."""

    def __init__(self) -> None:
        self._stats: Dict[str, LatencyStats] = {}

    def _key(self, port: int, proto: str) -> str:
        return f"{proto}:{port}"

    def record(self, port: int, proto: str, latency_ms: float) -> None:
        key = self._key(port, proto)
        if key not in self._stats:
            self._stats[key] = LatencyStats(port=port, proto=proto)
        self._stats[key].record(latency_ms)

    def get(self, port: int, proto: str) -> Optional[LatencyStats]:
        return self._stats.get(self._key(port, proto))

    def all_stats(self) -> List[LatencyStats]:
        return list(self._stats.values())

    def clear(self) -> None:
        self._stats.clear()
