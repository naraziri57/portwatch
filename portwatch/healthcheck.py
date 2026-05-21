"""Simple health-check endpoint that reports daemon liveness and last-scan metadata."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class HealthStatus:
    """Snapshot of daemon health at a point in time."""

    alive: bool = True
    last_scan_ts: Optional[float] = None  # epoch seconds
    last_scan_port_count: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = field(default=0.0, init=False)
    _start_ts: float = field(default_factory=time.monotonic, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._start_ts = time.monotonic()

    def record_scan(self, port_count: int) -> None:
        """Update metadata after a successful scan."""
        self.last_scan_ts = time.time()
        self.last_scan_port_count = port_count
        self.last_error = None

    def record_error(self, error: str) -> None:
        """Store the most recent scan error message."""
        self.last_error = error

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict (excludes private fields)."""
        self.uptime_seconds = round(time.monotonic() - self._start_ts, 2)
        d = asdict(self)
        d.pop("_start_ts", None)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def check_healthy(status: HealthStatus) -> bool:
    """Return True when the daemon is considered healthy."""
    return status.alive and status.last_error is None
