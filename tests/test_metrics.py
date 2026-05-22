"""Tests for portwatch.metrics."""
import pytest
from portwatch.metrics import Metrics, MetricsSnapshot, get_metrics


@pytest.fixture()
def m() -> Metrics:
    return Metrics()


class TestMetricsDefaults:
    def test_scans_start_at_zero(self, m):
        assert m.scans_total == 0

    def test_errors_start_at_zero(self, m):
        assert m.scan_errors == 0

    def test_events_total_start_at_zero(self, m):
        assert m.events_total == 0


class TestRecordScan:
    def test_increments_scans(self, m):
        m.record_scan()
        assert m.scans_total == 1

    def test_multiple_scans(self, m):
        for _ in range(5):
            m.record_scan()
        assert m.scans_total == 5


class TestRecordError:
    def test_increments_errors(self, m):
        m.record_error()
        assert m.scan_errors == 1

    def test_scan_error_independent_of_scan_count(self, m):
        m.record_scan()
        m.record_error()
        assert m.scans_total == 1
        assert m.scan_errors == 1


class TestRecordEvent:
    def test_new_kind_starts_at_one(self, m):
        m.record_event("opened")
        assert m.events_total == 1

    def test_same_kind_accumulates(self, m):
        m.record_event("opened")
        m.record_event("opened")
        assert m.events_total == 2

    def test_different_kinds_tracked_separately(self, m):
        m.record_event("opened")
        m.record_event("closed")
        snap = m.snapshot()
        assert snap.events_by_kind["opened"] == 1
        assert snap.events_by_kind["closed"] == 1


class TestSnapshot:
    def test_snapshot_is_immutable_copy(self, m):
        m.record_scan()
        snap = m.snapshot()
        m.record_scan()
        assert snap.scans_total == 1

    def test_snapshot_has_captured_at(self, m):
        snap = m.snapshot()
        assert snap.captured_at  # non-empty string

    def test_to_dict_keys(self, m):
        d = m.snapshot().to_dict()
        assert set(d) == {"scans_total", "scan_errors", "events_total",
                          "events_by_kind", "captured_at"}


class TestReset:
    def test_reset_clears_scans(self, m):
        m.record_scan()
        m.reset()
        assert m.scans_total == 0

    def test_reset_clears_events(self, m):
        m.record_event("opened")
        m.reset()
        assert m.events_total == 0


def test_get_metrics_returns_same_instance():
    a = get_metrics()
    b = get_metrics()
    assert a is b
