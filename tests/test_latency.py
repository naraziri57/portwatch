"""Tests for portwatch.latency."""
import pytest
from portwatch.latency import LatencyStats, LatencyTracker


# ---------------------------------------------------------------------------
# LatencyStats validation
# ---------------------------------------------------------------------------

def test_invalid_port_raises():
    with pytest.raises(ValueError, match="port"):
        LatencyStats(port=0, proto="tcp")


def test_port_too_high_raises():
    with pytest.raises(ValueError, match="port"):
        LatencyStats(port=70000, proto="tcp")


def test_invalid_proto_raises():
    with pytest.raises(ValueError, match="proto"):
        LatencyStats(port=80, proto="icmp")


def test_valid_udp_accepted():
    s = LatencyStats(port=53, proto="udp")
    assert s.proto == "udp"


# ---------------------------------------------------------------------------
# LatencyStats metrics
# ---------------------------------------------------------------------------

def _stats() -> LatencyStats:
    s = LatencyStats(port=443, proto="tcp")
    for v in [10.0, 20.0, 30.0]:
        s.record(v)
    return s


def test_sample_count():
    assert _stats().sample_count == 3


def test_mean_ms():
    assert _stats().mean_ms == pytest.approx(20.0)


def test_min_ms():
    assert _stats().min_ms == pytest.approx(10.0)


def test_max_ms():
    assert _stats().max_ms == pytest.approx(30.0)


def test_stdev_ms_none_single_sample():
    s = LatencyStats(port=80, proto="tcp")
    s.record(5.0)
    assert s.stdev_ms is None


def test_stdev_ms_calculated():
    s = _stats()
    assert s.stdev_ms is not None and s.stdev_ms > 0


def test_mean_none_when_empty():
    s = LatencyStats(port=80, proto="tcp")
    assert s.mean_ms is None


def test_negative_latency_raises():
    s = LatencyStats(port=80, proto="tcp")
    with pytest.raises(ValueError):
        s.record(-1.0)


def test_to_dict_contains_required_keys():
    d = _stats().to_dict()
    for key in ("port", "proto", "sample_count", "mean_ms", "min_ms", "max_ms", "stdev_ms"):
        assert key in d


# ---------------------------------------------------------------------------
# LatencyTracker
# ---------------------------------------------------------------------------

def test_tracker_starts_empty():
    t = LatencyTracker()
    assert t.all_stats() == []


def test_tracker_records_sample():
    t = LatencyTracker()
    t.record(80, "tcp", 5.0)
    s = t.get(80, "tcp")
    assert s is not None
    assert s.sample_count == 1


def test_tracker_accumulates_samples():
    t = LatencyTracker()
    t.record(80, "tcp", 5.0)
    t.record(80, "tcp", 10.0)
    assert t.get(80, "tcp").sample_count == 2


def test_tracker_separate_keys_for_different_ports():
    t = LatencyTracker()
    t.record(80, "tcp", 5.0)
    t.record(443, "tcp", 8.0)
    assert len(t.all_stats()) == 2


def test_tracker_get_missing_returns_none():
    t = LatencyTracker()
    assert t.get(9999, "tcp") is None


def test_tracker_clear_removes_all():
    t = LatencyTracker()
    t.record(80, "tcp", 1.0)
    t.clear()
    assert t.all_stats() == []
