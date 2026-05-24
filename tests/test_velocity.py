"""Tests for portwatch.velocity."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.scanner import PortEntry
from portwatch.velocity import VelocityStats, VelocityTracker


def _entry(port: int = 8080, proto: str = "tcp") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process="svc")


def _ev(port: int = 8080, proto: str = "tcp", kind: str = "opened") -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port, proto))


# --- VelocityStats ---

class TestVelocityStats:
    def test_initial_count_zero(self):
        s = VelocityStats(port=80, proto="tcp", window_seconds=60)
        assert s.count() == 0

    def test_record_increases_count(self):
        s = VelocityStats(port=80, proto="tcp", window_seconds=60)
        s.record(ts=time.time())
        assert s.count() == 1

    def test_old_events_evicted(self):
        s = VelocityStats(port=80, proto="tcp", window_seconds=10)
        now = time.time()
        s.record(ts=now - 20)  # outside window
        s.record(ts=now - 5)   # inside window
        assert s.count(now=now) == 1

    def test_rate_is_count_over_window(self):
        s = VelocityStats(port=80, proto="tcp", window_seconds=100)
        now = time.time()
        for i in range(10):
            s.record(ts=now - i)
        assert abs(s.rate(now=now) - 10 / 100) < 1e-9

    def test_to_dict_has_required_keys(self):
        s = VelocityStats(port=443, proto="tcp", window_seconds=60)
        d = s.to_dict()
        assert "port" in d
        assert "proto" in d
        assert "event_count" in d
        assert "rate_per_second" in d


# --- VelocityTracker ---

class TestVelocityTrackerValidation:
    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            VelocityTracker(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            VelocityTracker(window_seconds=-1)


class TestVelocityTracker:
    def test_record_event_creates_stats(self):
        t = VelocityTracker(window_seconds=60)
        t.record_event(_ev(8080))
        assert t.get(8080, "tcp") is not None

    def test_different_ports_tracked_independently(self):
        t = VelocityTracker(window_seconds=60)
        t.record_event(_ev(80))
        t.record_event(_ev(443))
        assert t.get(80, "tcp") is not None
        assert t.get(443, "tcp") is not None

    def test_all_stats_returns_list(self):
        t = VelocityTracker(window_seconds=60)
        t.record_event(_ev(80))
        t.record_event(_ev(443))
        assert len(t.all_stats()) == 2

    def test_hot_ports_filters_by_threshold(self):
        t = VelocityTracker(window_seconds=60)
        now = time.time()
        # pump 30 events in window -> rate = 0.5/s
        for i in range(30):
            t.record_event(_ev(9000), ts=now - i * 0.5)
        # one quiet port
        t.record_event(_ev(1234), ts=now - 59)
        hot = t.hot_ports(threshold=0.1)
        ports = [h["port"] for h in hot]
        assert 9000 in ports

    def test_get_unknown_port_returns_none(self):
        t = VelocityTracker(window_seconds=60)
        assert t.get(9999, "tcp") is None
