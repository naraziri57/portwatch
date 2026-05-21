"""Rate limiting for port scan cycles to avoid CPU thrash."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimiter:
    """Enforces a minimum interval between scan cycles."""

    min_interval: float  # seconds
    _last_run: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.min_interval <= 0:
            raise ValueError("min_interval must be positive")

    def ready(self) -> bool:
        """Return True if enough time has passed since the last run."""
        if self._last_run is None:
            return True
        return (time.monotonic() - self._last_run) >= self.min_interval

    def wait(self) -> None:
        """Block until the next run is allowed."""
        if self._last_run is not None:
            elapsed = time.monotonic() - self._last_run
            remaining = self.min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def mark(self) -> None:
        """Record that a run just completed."""
        self._last_run = time.monotonic()

    def time_until_ready(self) -> float:
        """Return seconds until next run is allowed (0 if already ready)."""
        if self._last_run is None:
            return 0.0
        elapsed = time.monotonic() - self._last_run
        return max(0.0, self.min_interval - elapsed)
