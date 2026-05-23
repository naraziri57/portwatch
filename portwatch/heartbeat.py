"""Periodic heartbeat emitter for portwatch daemon health signalling."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class HeartbeatConfig:
    interval: float = 60.0  # seconds between heartbeats
    on_beat: Optional[Callable[["HeartbeatState"], None]] = None

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("interval must be positive")


@dataclass
class HeartbeatState:
    beats: int = 0
    last_beat_at: Optional[float] = None
    started_at: float = field(default_factory=time.monotonic)

    def record_beat(self) -> None:
        self.beats += 1
        self.last_beat_at = time.monotonic()

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def to_dict(self) -> dict:
        return {
            "beats": self.beats,
            "last_beat_at": self.last_beat_at,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


class Heartbeat:
    """Tracks heartbeat timing and fires a callback when a beat is due."""

    def __init__(self, config: HeartbeatConfig) -> None:
        self._config = config
        self._state = HeartbeatState()
        self._next_beat: float = time.monotonic() + config.interval

    @property
    def state(self) -> HeartbeatState:
        return self._state

    def tick(self) -> bool:
        """Call periodically. Returns True if a beat was emitted."""
        now = time.monotonic()
        if now < self._next_beat:
            return False
        self._state.record_beat()
        self._next_beat = now + self._config.interval
        if self._config.on_beat is not None:
            self._config.on_beat(self._state)
        return True

    def force_beat(self) -> None:
        """Emit a beat immediately regardless of timing."""
        self._state.record_beat()
        self._next_beat = time.monotonic() + self._config.interval
        if self._config.on_beat is not None:
            self._config.on_beat(self._state)

    def reset(self) -> None:
        self._state = HeartbeatState()
        self._next_beat = time.monotonic() + self._config.interval
