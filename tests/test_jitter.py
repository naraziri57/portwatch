"""Tests for portwatch.jitter."""

import pytest
from datetime import datetime, timedelta

from portwatch.jitter import JitterStats, JitterTracker


# ---------------------------------------------------------------------------
# JitterStats
# ---------------------------------------------------------------------------

class TestJitterStats:
    def _stats(self):
        return JitterStats(port=443, proto="tcp")

    def test_sample_count_starts_at_zero(self):
        assert self._stats().sample_count == 0

    def test_mean_interval_none_when_single_sample(self):
        s = self._stats()
        s.record(datetime(2024, 1, 1, 12, 0, 0))
        assert s.mean_interval is None

    def test_mean_interval_calculated(self):
        s = self._stats()
        base = datetime(2024, 1, 1, 12, 0, 0)
        s.record(base)
        s.record(base + timedelta(seconds=10))
        s.record(base + timedelta(seconds=20))
        assert s.mean_interval == pytest.approx(10.0)

    def test_stdev_none_when_fewer_than_three(self):
        s = self._stats()
        base = datetime(2024, 1, 1, 12, 0, 0)
        s.record(base)
        s.record(base + timedelta(seconds=10))
        assert s.stdev_interval is None

    def test_not_jittery_with_regular_intervals(self):
        s = self._stats()
        base = datetime(2024, 1, 1, 12, 0, 0)
        for i in range(6):
            s.record(base + timedelta(seconds=i * 10))
        assert not s.is_jittery(cv_threshold=0.5)

    def test_jittery_with_irregular_intervals(self):
        s = self._stats()
        base = datetime(2024, 1, 1, 12, 0, 0)
        offsets = [0, 1, 30, 31, 120, 121]
        for off in offsets:
            s.record(base + timedelta(seconds=off))
        assert s.is_jittery(cv_threshold=0.5)

    def test_to_dict_has_required_keys(self):
        s = self._stats()
        d = s.to_dict()
        for key in ("port", "proto", "sample_count", "mean_interval", "stdev_interval", "jittery"):
            assert key in d

    def test_to_dict_port_matches(self):
        s = self._stats()
        assert s.to_dict()["port"] == 443


# ---------------------------------------------------------------------------
# JitterTracker
# ---------------------------------------------------------------------------

class TestJitterTracker:
    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError):
            JitterTracker(cv_threshold=0)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError):
            JitterTracker(cv_threshold=-1.0)

    def test_all_stats_empty_initially(self):
        tracker = JitterTracker()
        assert tracker.all_stats() == []

    def test_record_creates_entry(self):
        tracker = JitterTracker()
        tracker.record(80, "tcp", datetime(2024, 1, 1, 12, 0, 0))
        assert len(tracker.all_stats()) == 1

    def test_different_ports_tracked_independently(self):
        tracker = JitterTracker()
        base = datetime(2024, 1, 1, 12, 0, 0)
        tracker.record(80, "tcp", base)
        tracker.record(443, "tcp", base)
        assert len(tracker.all_stats()) == 2

    def test_jittery_ports_returns_only_jittery(self):
        tracker = JitterTracker(cv_threshold=0.5)
        base = datetime(2024, 1, 1, 12, 0, 0)
        # regular port
        for i in range(6):
            tracker.record(80, "tcp", base + timedelta(seconds=i * 10))
        # jittery port
        for off in [0, 1, 50, 51, 200, 201]:
            tracker.record(9999, "tcp", base + timedelta(seconds=off))
        jittery = tracker.jittery_ports()
        assert len(jittery) == 1
        assert jittery[0].port == 9999
