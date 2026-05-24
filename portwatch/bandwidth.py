"""Track estimated bandwidth usage per open port over time."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BandwidthSample:
    port: int
    proto: str
    bytes_in: int
    bytes_out: int
    timestamp: float = field(default_factory=time.time)

    def total_bytes(self) -> int:
        return self.bytes_in + self.bytes_out

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BandwidthSample":
        return cls(
            port=d["port"],
            proto=d["proto"],
            bytes_in=d["bytes_in"],
            bytes_out=d["bytes_out"],
            timestamp=d["timestamp"],
        )


@dataclass
class BandwidthStats:
    port: int
    proto: str
    samples: List[BandwidthSample] = field(default_factory=list)

    def add(self, sample: BandwidthSample) -> None:
        self.samples.append(sample)

    def total_bytes(self) -> int:
        return sum(s.total_bytes() for s in self.samples)

    def average_bytes(self) -> float:
        if not self.samples:
            return 0.0
        return self.total_bytes() / len(self.samples)

    def peak_sample(self) -> Optional[BandwidthSample]:
        if not self.samples:
            return None
        return max(self.samples, key=lambda s: s.total_bytes())

    def summary(self) -> str:
        peak = self.peak_sample()
        peak_str = f"{peak.total_bytes()}B" if peak else "n/a"
        return (
            f"{self.proto.upper()}:{self.port} "
            f"samples={len(self.samples)} "
            f"total={self.total_bytes()}B "
            f"avg={self.average_bytes():.1f}B "
            f"peak={peak_str}"
        )


class BandwidthTracker:
    def __init__(self) -> None:
        self._stats: Dict[str, BandwidthStats] = {}

    def _key(self, port: int, proto: str) -> str:
        return f"{proto}:{port}"

    def record(self, sample: BandwidthSample) -> None:
        key = self._key(sample.port, sample.proto)
        if key not in self._stats:
            self._stats[key] = BandwidthStats(port=sample.port, proto=sample.proto)
        self._stats[key].add(sample)

    def stats_for(self, port: int, proto: str) -> Optional[BandwidthStats]:
        return self._stats.get(self._key(port, proto))

    def all_stats(self) -> List[BandwidthStats]:
        return list(self._stats.values())

    def clear(self) -> None:
        self._stats.clear()
