"""Watchdog: detects if the watcher loop has stalled and records the condition."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class WatchdogState:
    """Tracks liveness of the watcher loop."""

    timeout: float  # seconds before declaring a stall
    on_stall: Callable[[], None] = field(repr=False)
    _last_ping: float = field(default_factory=time.monotonic, init=False, repr=False)
    _stalled: bool = field(default=False, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def ping(self) -> None:
        """Called by the watcher loop each iteration to signal liveness."""
        with self._lock:
            self._last_ping = time.monotonic()
            self._stalled = False

    def is_stalled(self) -> bool:
        with self._lock:
            return self._stalled

    def seconds_since_ping(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_ping

    def check(self) -> None:
        """Evaluate liveness; invoke on_stall callback if timeout exceeded."""
        elapsed = self.seconds_since_ping()
        if elapsed >= self.timeout:
            with self._lock:
                if not self._stalled:
                    self._stalled = True
            self.on_stall()


class Watchdog:
    """Background thread that periodically checks whether the watcher loop is alive."""

    def __init__(
        self,
        timeout: float,
        on_stall: Callable[[], None],
        check_interval: Optional[float] = None,
    ) -> None:
        self._state = WatchdogState(timeout=timeout, on_stall=on_stall)
        self._check_interval = check_interval if check_interval is not None else max(1.0, timeout / 4)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def ping(self) -> None:
        self._state.ping()

    def is_stalled(self) -> bool:
        return self._state.is_stalled()

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="portwatch-watchdog")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._check_interval + 1)

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=self._check_interval):
            self._state.check()
