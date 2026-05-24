"""Tests for portwatch.lockout."""
import time
import pytest
from unittest.mock import patch

from portwatch.lockout import LockoutPolicy, LockoutTracker


# --- policy validation ---

class TestLockoutPolicyValidation:
    def test_defaults(self):
        p = LockoutPolicy()
        assert p.trigger_count == 5
        assert p.window_seconds == 60.0
        assert p.lockout_seconds == 300.0

    def test_zero_trigger_raises(self):
        with pytest.raises(ValueError, match="trigger_count"):
            LockoutPolicy(trigger_count=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            LockoutPolicy(window_seconds=-1)

    def test_zero_lockout_raises(self):
        with pytest.raises(ValueError, match="lockout_seconds"):
            LockoutPolicy(lockout_seconds=0)


# --- tracker behaviour ---

@pytest.fixture
def tracker():
    return LockoutTracker(LockoutPolicy(trigger_count=3, window_seconds=10.0, lockout_seconds=30.0))


class TestLockoutTracker:
    def test_not_locked_initially(self, tracker):
        assert not tracker.is_locked(80, "tcp")

    def test_below_threshold_no_lockout(self, tracker):
        tracker.record_event(80, "tcp")
        tracker.record_event(80, "tcp")
        assert not tracker.is_locked(80, "tcp")

    def test_at_threshold_triggers_lockout(self, tracker):
        tracker.record_event(80, "tcp")
        tracker.record_event(80, "tcp")
        triggered = tracker.record_event(80, "tcp")
        assert triggered is True
        assert tracker.is_locked(80, "tcp")

    def test_different_proto_independent(self, tracker):
        for _ in range(3):
            tracker.record_event(80, "tcp")
        assert tracker.is_locked(80, "tcp")
        assert not tracker.is_locked(80, "udp")

    def test_different_port_independent(self, tracker):
        for _ in range(3):
            tracker.record_event(80, "tcp")
        assert tracker.is_locked(80, "tcp")
        assert not tracker.is_locked(443, "tcp")

    def test_locked_ports_lists_locked(self, tracker):
        for _ in range(3):
            tracker.record_event(8080, "tcp")
        locked = tracker.locked_ports()
        assert (8080, "tcp") in locked

    def test_clear_removes_lockout(self, tracker):
        for _ in range(3):
            tracker.record_event(80, "tcp")
        assert tracker.is_locked(80, "tcp")
        tracker.clear(80, "tcp")
        assert not tracker.is_locked(80, "tcp")

    def test_lockout_expires(self, tracker):
        base = 1000.0
        with patch("portwatch.lockout.time.monotonic", return_value=base):
            for _ in range(3):
                tracker.record_event(80, "tcp")
        # advance past lockout_seconds (30)
        with patch("portwatch.lockout.time.monotonic", return_value=base + 31.0):
            assert not tracker.is_locked(80, "tcp")

    def test_events_outside_window_not_counted(self, tracker):
        base = 1000.0
        with patch("portwatch.lockout.time.monotonic", return_value=base):
            tracker.record_event(80, "tcp")
            tracker.record_event(80, "tcp")
        # advance past window (10s), add one more — should not trigger
        with patch("portwatch.lockout.time.monotonic", return_value=base + 11.0):
            triggered = tracker.record_event(80, "tcp")
        assert triggered is False
        with patch("portwatch.lockout.time.monotonic", return_value=base + 11.0):
            assert not tracker.is_locked(80, "tcp")
