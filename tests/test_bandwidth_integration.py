"""Integration tests for bandwidth tracking end-to-end."""
import time
import pytest
from portwatch.bandwidth import BandwidthSample, BandwidthTracker


def _sample(port=80, proto="tcp", bytes_in=0, bytes_out=0):
    return BandwidthSample(port=port, proto=proto, bytes_in=bytes_in, bytes_out=bytes_out)


class TestBandwidthLifecycle:
    def test_multiple_ports_tracked_independently(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=80, proto="tcp", bytes_in=100, bytes_out=50))
        tracker.record(_sample(port=443, proto="tcp", bytes_in=200, bytes_out=300))
        tracker.record(_sample(port=53, proto="udp", bytes_in=10, bytes_out=10))

        assert tracker.stats_for(80, "tcp").total_bytes() == 150
        assert tracker.stats_for(443, "tcp").total_bytes() == 500
        assert tracker.stats_for(53, "udp").total_bytes() == 20

    def test_samples_accumulate_over_time(self):
        tracker = BandwidthTracker()
        for i in range(5):
            tracker.record(_sample(port=8080, proto="tcp", bytes_in=100, bytes_out=100))
        stats = tracker.stats_for(8080, "tcp")
        assert len(stats.samples) == 5
        assert stats.total_bytes() == 1000
        assert stats.average_bytes() == 200.0

    def test_peak_detection_across_samples(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=9000, proto="tcp", bytes_in=10, bytes_out=10))
        tracker.record(_sample(port=9000, proto="tcp", bytes_in=5000, bytes_out=5000))
        tracker.record(_sample(port=9000, proto="tcp", bytes_in=20, bytes_out=20))
        peak = tracker.stats_for(9000, "tcp").peak_sample()
        assert peak.total_bytes() == 10000

    def test_clear_and_reuse(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=80, proto="tcp", bytes_in=999, bytes_out=999))
        tracker.clear()
        assert tracker.stats_for(80, "tcp") is None
        tracker.record(_sample(port=80, proto="tcp", bytes_in=1, bytes_out=1))
        assert tracker.stats_for(80, "tcp").total_bytes() == 2

    def test_summary_string_stable(self):
        tracker = BandwidthTracker()
        tracker.record(_sample(port=22, proto="tcp", bytes_in=256, bytes_out=128))
        summary = tracker.stats_for(22, "tcp").summary()
        assert "TCP:22" in summary
        assert "total=384B" in summary
