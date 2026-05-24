"""Circuit breaker for scan failures — pauses scanning after repeated errors."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class BreakerState(str, Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # tripped, scans paused
    HALF_OPEN = "half_open"  # testing recovery


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 60.0  # seconds before trying half-open
    _failures: int = field(default=0, init=False, repr=False)
    _state: BreakerState = field(default=BreakerState.CLOSED, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")

    @property
    def state(self) -> BreakerState:
        if self._state == BreakerState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = BreakerState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Return True if a scan should proceed."""
        return self.state in (BreakerState.CLOSED, BreakerState.HALF_OPEN)

    def record_success(self) -> None:
        """Call after a successful scan."""
        self._failures = 0
        self._state = BreakerState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        """Call after a failed scan."""
        self._failures += 1
        if self._state == BreakerState.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = BreakerState.OPEN
            self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the breaker to closed."""
        self._failures = 0
        self._state = BreakerState.CLOSED
        self._opened_at = None

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "failures": self._failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "opened_at": self._opened_at,
        }
