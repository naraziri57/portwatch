"""Tests for portwatch.watchdog."""

from __future__ import annotations

import time
import threading
from unittest.mock import MagicMock

import pytest

from portwatch.watchdog import Watchdog, WatchdogState


# ---------------------------------------------------------------------------
# WatchdogState unit tests
# ---------------------------------------------------------------------------


class TestWatchdogState:
    def _make_state(self, timeout: float = 5.0):
        cb = MagicMock()
        state = WatchdogState(timeout=timeout, on_stall=cb)
        return state, cb

    def test_not_stalled_initially(self):
        state, _ = self._make_state()
        assert not state.is_stalled()

    def test_check_does_not_stall_when_fresh(self):
        state, cb = self._make_state(timeout=60.0)
        state.check()
        assert not state.is_stalled()
        cb.assert_not_called()

    def test_check_stalls_after_timeout(self):
        state, cb = self._make_state(timeout=0.0)
        # With timeout=0, any elapsed time triggers stall
        time.sleep(0.01)
        state.check()
        assert state.is_stalled()
        cb.assert_called_once()

    def test_ping_clears_stall(self):
        state, cb = self._make_state(timeout=0.0)
        time.sleep(0.01)
        state.check()
        assert state.is_stalled()
        state.ping()
        assert not state.is_stalled()

    def test_on_stall_called_only_once_per_stall(self):
        state, cb = self._make_state(timeout=0.0)
        time.sleep(0.01)
        state.check()
        state.check()  # second call should not re-fire
        cb.assert_called_once()

    def test_seconds_since_ping_increases(self):
        state, _ = self._make_state()
        t0 = state.seconds_since_ping()
        time.sleep(0.05)
        t1 = state.seconds_since_ping()
        assert t1 > t0


# ---------------------------------------------------------------------------
# Watchdog integration tests
# ---------------------------------------------------------------------------


class TestWatchdog:
    def test_no_stall_when_pinged_regularly(self):
        stall_called = threading.Event()
        dog = Watchdog(timeout=0.3, on_stall=lambda: stall_called.set(), check_interval=0.05)
        dog.start()
        try:
            for _ in range(6):
                dog.ping()
                time.sleep(0.04)
            assert not stall_called.is_set()
        finally:
            dog.stop()

    def test_stall_detected_when_ping_stops(self):
        stall_called = threading.Event()
        dog = Watchdog(timeout=0.1, on_stall=lambda: stall_called.set(), check_interval=0.05)
        dog.start()
        dog.ping()
        # Do NOT ping again; wait for stall detection
        triggered = stall_called.wait(timeout=1.0)
        dog.stop()
        assert triggered, "Expected stall to be detected"

    def test_stop_joins_thread(self):
        dog = Watchdog(timeout=10.0, on_stall=lambda: None, check_interval=0.05)
        dog.start()
        assert dog._thread is not None
        dog.stop()
        assert not dog._thread.is_alive()
