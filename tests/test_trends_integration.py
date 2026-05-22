"""Integration tests: TrendTracker driven by realistic open/close sequences."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from portwatch.trends import TrendTracker


@pytest.fixture()
def tracker():
    return TrendTracker(window_minutes=30)


class TestTrendIntegration:
    def test_steady_open_port_not_flapping(self, tracker):
        """A port that only opens (never closes) is not flapping."""
        for _ in range(10):
            tracker.record_open(80, "tcp")
        assert tracker.flapping_ports(threshold=3) == []

    def test_alternating_open_close_detected_as_flapping(self, tracker):
        for _ in range(5):
            tracker.record_open(8080, "tcp")
            tracker.record_close(8080, "tcp")
        flapping = tracker.flapping_ports(threshold=3)
        ports = [t.port for t in flapping]
        assert 8080 in ports

    def test_multiple_ports_independent_flap_detection(self, tracker):
        # 8080 flaps; 443 only opens
        for _ in range(4):
            tracker.record_open(8080, "tcp")
            tracker.record_close(8080, "tcp")
        for _ in range(4):
            tracker.record_open(443, "tcp")

        flapping_ports = {t.port for t in tracker.flapping_ports(threshold=3)}
        assert 8080 in flapping_ports
        assert 443 not in flapping_ports

    def test_stale_flapping_port_evicted(self, tracker):
        for _ in range(5):
            tracker.record_open(22, "tcp")
            tracker.record_close(22, "tcp")

        # Age the entry beyond the window
        key = (22, "tcp")
        tracker._data[key].last_seen = datetime.utcnow() - timedelta(hours=1)

        assert tracker.flapping_ports(threshold=3) == []

    def test_reset_clears_flapping_state(self, tracker):
        for _ in range(5):
            tracker.record_open(3306, "tcp")
            tracker.record_close(3306, "tcp")
        tracker.reset()
        assert tracker.flapping_ports(threshold=3) == []
        assert tracker.all_trends() == []
