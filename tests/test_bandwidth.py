"""Tests for portwatch.bandwidth."""
import time
import pytest
from portwatch.bandwidth import BandwidthSample, BandwidthStats, BandwidthTracker


def _sample(port=8080, proto="tcp", bytes_in=100, bytes_out=200, ts=None):
    return BandwidthSample(
        port=port,
        proto=proto,
        bytes_in=bytes_in,
        bytes_out=bytes_out,
        timestamp=ts if ts is not None else time.time(),
    )


class TestBandwidthSample:
    def test_total_bytes(self):
        s = _sample(bytes_in=100, bytes_out=200)
        assert s.total_bytes() == 300

    def test_to_dict_roundtrip(self):
        s = _sample()
        d = s.to_dict()
        s2 = BandwidthSample.from_dict(d)
        assert s2.port == s.port
        assert s2.proto == s.proto
        assert s2.bytes_in == s.bytes_in
        assert s2.bytes_out == s.bytes_out
        assert s2.timestamp == s.timestamp

    def test_to_dict_has_all_keys(self):
        d = _sample().to_dict()
        for key in ("port", "proto", "bytes_in", "bytes_out", "timestamp"):
            assert key in d


class TestBandwidthStats:
    def test_empty_total_is_zero(self):
        stats = BandwidthStats(port=80, proto="tcp")
        assert stats.total_bytes() == 0

    def test_empty_average_is_zero(self):
        stats = BandwidthStats(port=80, proto="tcp")
        assert stats.average_bytes() == 0.0

    def test_empty_peak_is_none(self):
        stats = BandwidthStats(port=80, proto="tcp")
        assert stats.peak_sample() is None

    def test_add_increases_total(self):
        stats = BandwidthStats(port=80, proto="tcp")
        stats.add(_sample(bytes_in=50, bytes_out=50))
        assert stats.total_bytes() == 100

    def test_peak_is_highest(self):
        stats = BandwidthStats(port=80, proto="tcp")
        stats.add(_sample(bytes_in=10, bytes_out=10))
        stats.add(_sample(bytes_in=500, bytes_out=500))
        stats.add(_sample(bytes_in=5, bytes_out=5))
        assert stats.peak_sample().total_bytes() == 1000

    def test_average_correct(self):
        stats = BandwidthStats(port=80, proto="tcp")
        stats.add(_sample(bytes_in=100, bytes_out=100))
        stats.add(_sample(bytes_in=200, bytes_out=200))
        assert stats.average_bytes() == 300.0

    def test_summary_contains_port(self):
        stats = BandwidthStats(port=443, proto="tcp")
        stats.add(_sample(port=443))
        assert "443" in stats.summary()

    def test_summary_contains_proto(self):
        stats = BandwidthStats(port=53, proto="udp")
        stats.add(_sample(port=53, proto="udp"))
        assert "UDP" in stats.summary()


class TestBandwidthTracker:
    def test_record_and_retrieve(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=80, proto="tcp"))
        result = tracker.stats_for(80, "tcp")
        assert result is not None
        assert result.port == 80

    def test_missing_returns_none(self):
        tracker = BandwidthTracker()
        assert tracker.stats_for(9999, "tcp") is None

    def test_multiple_samples_accumulate(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=80, proto="tcp", bytes_in=100, bytes_out=100))
        tracker.record(_sample(port=80, proto="tcp", bytes_in=200, bytes_out=200))
        assert tracker.stats_for(80, "tcp").total_bytes() == 600

    def test_different_ports_are_separate(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=80, proto="tcp"))
        tracker.record(_sample(port=443, proto="tcp"))
        assert len(tracker.all_stats()) == 2

    def test_clear_removes_all(self):
        tracker = BandwidthTracker()
        tracker.record(_sample())
        tracker.clear()
        assert tracker.all_stats() == []
