"""Anomaly detection: flag ports that appear outside expected time windows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional

from portwatch.scanner import PortEntry


@dataclass
class TimeWindow:
    """A daily time window defined by start and end (HH:MM strings)."""

    start: str  # e.g. "08:00"
    end: str    # e.g. "18:00"

    _TIME_RE = re.compile(r'^\d{2}:\d{2}$')

    def __post_init__(self) -> None:
        for val in (self.start, self.end):
            if not self._TIME_RE.match(val):
                raise ValueError(f"Time must be HH:MM, got {val!r}")

    def _parse(self, t: str) -> time:
        h, m = t.split(':')
        return time(int(h), int(m))

    def contains(self, dt: Optional[datetime] = None) -> bool:
        """Return True if *dt* (default: now) falls within this window."""
        now = (dt or datetime.now()).time().replace(second=0, microsecond=0)
        s, e = self._parse(self.start), self._parse(self.end)
        if s <= e:
            return s <= now <= e
        # overnight window e.g. 22:00 – 06:00
        return now >= s or now <= e

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, d: dict) -> "TimeWindow":
        return cls(start=d["start"], end=d["end"])


@dataclass
class AnomalyRule:
    """Flag a port/proto combination when seen outside *allowed_windows*."""

    port: int
    proto: str = "tcp"
    allowed_windows: List[TimeWindow] = field(default_factory=list)
    description: str = ""

    def is_anomalous(self, entry: PortEntry, dt: Optional[datetime] = None) -> bool:
        """Return True if *entry* matches this rule and is outside all windows."""
        if entry.port != self.port or entry.proto.lower() != self.proto.lower():
            return False
        if not self.allowed_windows:
            return True  # no windows defined → always anomalous
        return not any(w.contains(dt) for w in self.allowed_windows)

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "allowed_windows": [w.to_dict() for w in self.allowed_windows],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AnomalyRule":
        return cls(
            port=int(d["port"]),
            proto=d.get("proto", "tcp"),
            allowed_windows=[TimeWindow.from_dict(w) for w in d.get("allowed_windows", [])],
            description=d.get("description", ""),
        )


def detect_anomalies(
    ports: List[PortEntry],
    rules: List[AnomalyRule],
    dt: Optional[datetime] = None,
) -> List[PortEntry]:
    """Return entries that match at least one anomaly rule at time *dt*."""
    flagged: List[PortEntry] = []
    for entry in ports:
        if any(r.is_anomalous(entry, dt) for r in rules):
            flagged.append(entry)
    return flagged
