"""Integration: metrics accumulate correctly across multiple watcher cycles."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from portwatch.metrics import Metrics
from portwatch.scanner import PortEntry


def _entry(port: int, proto: str = "tcp") -> PortEntry:
    return PortEntry(port=port, proto=proto, local_address="0.0.0.0", process=None)


@pytest.fixture()
def metrics() -> Metrics:
    return Metrics()


class TestMetricsLifecycle:
    def test_scan_then_error_both_recorded(self, metrics):
        metrics.record_scan()
        metrics.record_error()
        assert metrics.scans_total == 1
        assert metrics.scan_errors == 1

    def test_events_accumulate_across_scans(self, metrics):
        for _ in range(3):
            metrics.record_scan()
            metrics.record_event("opened")
        assert metrics.scans_total == 3
        assert metrics.events_total == 3

    def test_mixed_event_kinds(self, metrics):
        metrics.record_event("opened")
        metrics.record_event("opened")
        metrics.record_event("closed")
        snap = metrics.snapshot()
        assert snap.events_by_kind == {"opened": 2, "closed": 1}
        assert snap.events_total == 3

    def test_reset_after_digest(self, metrics):
        metrics.record_scan()
        metrics.record_event("opened")
        metrics.reset()
        snap = metrics.snapshot()
        assert snap.scans_total == 0
        assert snap.events_total == 0
        assert snap.events_by_kind == {}

    def test_snapshot_to_dict_roundtrip(self, metrics):
        metrics.record_scan()
        metrics.record_event("closed")
        d = metrics.snapshot().to_dict()
        assert d["scans_total"] == 1
        assert d["events_by_kind"]["closed"] == 1
        assert isinstance(d["captured_at"], str)
