"""Port scan sampling: record periodic snapshots for statistical analysis."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from portwatch.scanner import PortEntry


@dataclass
class SamplePoint:
    timestamp: float
    port_count: int
    ports: List[dict]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "port_count": self.port_count,
            "ports": self.ports,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SamplePoint":
        return cls(
            timestamp=float(d["timestamp"]),
            port_count=int(d["port_count"]),
            ports=list(d["ports"]),
        )

    @classmethod
    def capture(cls, ports: List[PortEntry]) -> "SamplePoint":
        return cls(
            timestamp=time.time(),
            port_count=len(ports),
            ports=[{"port": p.port, "proto": p.proto, "process": p.process} for p in ports],
        )


@dataclass
class SampleStore:
    path: Path
    max_samples: int = 1440  # ~24 h at 1-min intervals
    _samples: List[SamplePoint] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_samples < 1:
            raise ValueError("max_samples must be >= 1")
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        raw = json.loads(self.path.read_text())
        self._samples = [SamplePoint.from_dict(r) for r in raw]

    def record(self, ports: List[PortEntry]) -> SamplePoint:
        sp = SamplePoint.capture(ports)
        self._samples.append(sp)
        if len(self._samples) > self.max_samples:
            self._samples = self._samples[-self.max_samples :]
        self.path.write_text(json.dumps([s.to_dict() for s in self._samples]))
        return sp

    def all_samples(self) -> List[SamplePoint]:
        return list(self._samples)

    def latest(self) -> Optional[SamplePoint]:
        return self._samples[-1] if self._samples else None

    def average_port_count(self) -> float:
        if not self._samples:
            return 0.0
        return sum(s.port_count for s in self._samples) / len(self._samples)
