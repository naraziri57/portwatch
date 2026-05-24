"""Integration tests for latency tracking end-to-end."""
import pytest
from portwatch.latency import LatencyStats, LatencyTracker


def _populated_tracker() -> LatencyTracker:
    t = LatencyTracker()
    samples = {
        (80,  "tcp"): [12.0, 14.0, 13.0],
        (443, "tcp"): [5.0, 6.0],
        (53,  "udp"): [1.0],
    }
    for (port, proto), values in samples.items():
        for v in values:
            t.record(port, proto, v)
    return t


class TestLatencyTrackerLifecycle:
    def test_all_ports_present(self):
        t = _populated_tracker()
        ports = {s.port for s in t.all_stats()}
        assert ports == {80, 443, 53}

    def test_mean_computed_correctly(self):
        t = _populated_tracker()
        s = t.get(80, "tcp")
        assert s.mean_ms == pytest.approx(13.0)

    def test_min_max_correct(self):
        t = _populated_tracker()
        s = t.get(80, "tcp")
        assert s.min_ms == pytest.approx(12.0)
        assert s.max_ms == pytest.approx(14.0)

    def test_single_sample_no_stdev(self):
        t = _populated_tracker()
        s = t.get(53, "udp")
        assert s.stdev_ms is None

    def test_to_dict_round_trip(self):
        t = _populated_tracker()
        s = t.get(443, "tcp")
        d = s.to_dict()
        assert d["port"] == 443
        assert d["proto"] == "tcp"
        assert d["sample_count"] == 2
        assert d["mean_ms"] == pytest.approx(5.5)

    def test_clear_then_reuse(self):
        t = _populated_tracker()
        t.clear()
        assert t.all_stats() == []
        t.record(8080, "tcp", 7.0)
        assert len(t.all_stats()) == 1
