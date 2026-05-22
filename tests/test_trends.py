"""Tests for portwatch.trends."""

from datetime import datetime, timedelta

import pytest

from portwatch.trends import PortTrend, TrendTracker


# ---------------------------------------------------------------------------
# PortTrend unit tests
# ---------------------------------------------------------------------------

class TestPortTrend:
    def test_total_events(self):
        t = PortTrend(port=80, proto="tcp", opens=2, closes=3)
        assert t.total_events == 5

    def test_not_flapping_below_threshold(self):
        t = PortTrend(port=80, proto="tcp", opens=2, closes=2)
        assert not t.is_flapping(threshold=3)

    def test_flapping_at_threshold(self):
        t = PortTrend(port=80, proto="tcp", opens=3, closes=3)
        assert t.is_flapping(threshold=3)

    def test_not_flapping_one_side_only(self):
        t = PortTrend(port=80, proto="tcp", opens=5, closes=1)
        assert not t.is_flapping(threshold=3)

    def test_to_dict_keys(self):
        t = PortTrend(port=443, proto="tcp")
        d = t.to_dict()
        assert set(d.keys()) == {"port", "proto", "opens", "closes", "last_seen"}


# ---------------------------------------------------------------------------
# TrendTracker validation
# ---------------------------------------------------------------------------

def test_zero_window_raises():
    with pytest.raises(ValueError):
        TrendTracker(window_minutes=0)


def test_negative_window_raises():
    with pytest.raises(ValueError):
        TrendTracker(window_minutes=-5)


# ---------------------------------------------------------------------------
# TrendTracker behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracker():
    return TrendTracker(window_minutes=60)


def test_record_open_increments(tracker):
    tracker.record_open(80, "tcp")
    tracker.record_open(80, "tcp")
    trends = tracker.all_trends()
    assert len(trends) == 1
    assert trends[0].opens == 2


def test_record_close_increments(tracker):
    tracker.record_close(22, "tcp")
    trends = tracker.all_trends()
    assert trends[0].closes == 1


def test_proto_case_insensitive(tracker):
    tracker.record_open(80, "TCP")
    tracker.record_open(80, "tcp")
    assert len(tracker.all_trends()) == 1


def test_different_ports_tracked_separately(tracker):
    tracker.record_open(80, "tcp")
    tracker.record_open(443, "tcp")
    assert len(tracker.all_trends()) == 2


def test_flapping_ports_returned(tracker):
    for _ in range(4):
        tracker.record_open(8080, "tcp")
        tracker.record_close(8080, "tcp")
    flapping = tracker.flapping_ports(threshold=3)
    assert any(t.port == 8080 for t in flapping)


def test_non_flapping_not_in_flapping_list(tracker):
    tracker.record_open(9000, "tcp")
    assert tracker.flapping_ports(threshold=3) == []


def test_evict_stale_removes_old_entries(tracker):
    tracker.record_open(80, "tcp")
    # Backdate the entry
    key = (80, "tcp")
    tracker._data[key].last_seen = datetime.utcnow() - timedelta(hours=2)
    tracker.evict_stale()
    assert len(tracker.all_trends()) == 0


def test_reset_clears_all(tracker):
    tracker.record_open(80, "tcp")
    tracker.reset()
    assert tracker.all_trends() == []
