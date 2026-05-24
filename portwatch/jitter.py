"""Jitter detection: flags ports whose open/close timing looks suspiciously irregular."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class JitterStats:
    port: int
    proto: str
    timestamps: List[float] = field(default_factory=list)

    def record(self, ts: datetime) -> None:
        self.timestamps.append(ts.timestamp())

    @property
    def sample_count(self) -> int:
        return len(self.timestamps)

    @property
    def mean_interval(self) -> Optional[float]:
        if len(self.timestamps) < 2:
            return None
        intervals = [
            self.timestamps[i + 1] - self.timestamps[i]
            for i in range(len(self.timestamps) - 1)
        ]
        return statistics.mean(intervals)

    @property
    def stdev_interval(self) -> Optional[float]:
        if len(self.timestamps) < 3:
            return None
        intervals = [
            self.timestamps[i + 1] - self.timestamps[i]
            for i in range(len(self.timestamps) - 1)
        ]
        return statistics.stdev(intervals)

    def is_jittery(self, cv_threshold: float = 0.5) -> bool:
        """Return True when coefficient of variation exceeds threshold."""
        mean = self.mean_interval
        stdev = self.stdev_interval
        if mean is None or stdev is None or mean == 0:
            return False
        return (stdev / mean) > cv_threshold

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "sample_count": self.sample_count,
            "mean_interval": self.mean_interval,
            "stdev_interval": self.stdev_interval,
            "jittery": self.is_jittery(),
        }


@dataclass
class JitterTracker:
    cv_threshold: float = 0.5
    _stats: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.cv_threshold <= 0:
            raise ValueError("cv_threshold must be positive")

    def _key(self, port: int, proto: str) -> str:
        return f"{proto}:{port}"

    def record(self, port: int, proto: str, ts: datetime) -> None:
        key = self._key(port, proto)
        if key not in self._stats:
            self._stats[key] = JitterStats(port=port, proto=proto)
        self._stats[key].record(ts)

    def jittery_ports(self) -> List[JitterStats]:
        return [
            s for s in self._stats.values()
            if s.is_jittery(self.cv_threshold)
        ]

    def all_stats(self) -> List[JitterStats]:
        return list(self._stats.values())
