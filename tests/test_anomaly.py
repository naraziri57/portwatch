"""Tests for portwatch.anomaly."""

from __future__ import annotations

from datetime import datetime

import pytest

from portwatch.anomaly import AnomalyRule, TimeWindow, detect_anomalies
from portwatch.scanner import PortEntry


def _entry(port: int = 8080, proto: str = "tcp", process: str = "app") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


# ---------------------------------------------------------------------------
# TimeWindow
# ---------------------------------------------------------------------------

class TestTimeWindow:
    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            TimeWindow(start="8:00", end="18:00")

    def test_contains_midday(self):
        w = TimeWindow("08:00", "18:00")
        assert w.contains(datetime(2024, 1, 1, 12, 0))

    def test_not_contains_before_start(self):
        w = TimeWindow("08:00", "18:00")
        assert not w.contains(datetime(2024, 1, 1, 7, 59))

    def test_not_contains_after_end(self):
        w = TimeWindow("08:00", "18:00")
        assert not w.contains(datetime(2024, 1, 1, 18, 1))

    def test_overnight_window_contains_midnight(self):
        w = TimeWindow("22:00", "06:00")
        assert w.contains(datetime(2024, 1, 1, 0, 30))

    def test_overnight_window_contains_evening(self):
        w = TimeWindow("22:00", "06:00")
        assert w.contains(datetime(2024, 1, 1, 23, 0))

    def test_overnight_window_not_contains_midday(self):
        w = TimeWindow("22:00", "06:00")
        assert not w.contains(datetime(2024, 1, 1, 12, 0))

    def test_roundtrip(self):
        w = TimeWindow("09:00", "17:30")
        assert TimeWindow.from_dict(w.to_dict()) == w


# ---------------------------------------------------------------------------
# AnomalyRule
# ---------------------------------------------------------------------------

class TestAnomalyRule:
    def test_no_windows_always_anomalous(self):
        rule = AnomalyRule(port=8080)
        assert rule.is_anomalous(_entry(8080), datetime(2024, 1, 1, 12, 0))

    def test_inside_window_not_anomalous(self):
        rule = AnomalyRule(port=8080, allowed_windows=[TimeWindow("08:00", "18:00")])
        assert not rule.is_anomalous(_entry(8080), datetime(2024, 1, 1, 12, 0))

    def test_outside_window_anomalous(self):
        rule = AnomalyRule(port=8080, allowed_windows=[TimeWindow("08:00", "18:00")])
        assert rule.is_anomalous(_entry(8080), datetime(2024, 1, 1, 3, 0))

    def test_wrong_port_not_flagged(self):
        rule = AnomalyRule(port=9090)
        assert not rule.is_anomalous(_entry(8080))

    def test_wrong_proto_not_flagged(self):
        rule = AnomalyRule(port=8080, proto="udp")
        assert not rule.is_anomalous(_entry(8080, proto="tcp"))

    def test_roundtrip(self):
        rule = AnomalyRule(
            port=443,
            proto="tcp",
            allowed_windows=[TimeWindow("00:00", "23:59")],
            description="always ok",
        )
        assert AnomalyRule.from_dict(rule.to_dict()).port == rule.port
        assert AnomalyRule.from_dict(rule.to_dict()).description == rule.description


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------

class TestDetectAnomalies:
    def test_empty_rules_returns_nothing(self):
        ports = [_entry(8080), _entry(443)]
        assert detect_anomalies(ports, []) == []

    def test_flags_matching_port_outside_window(self):
        rule = AnomalyRule(port=8080, allowed_windows=[TimeWindow("08:00", "18:00")])
        ports = [_entry(8080), _entry(443)]
        flagged = detect_anomalies(ports, [rule], dt=datetime(2024, 1, 1, 2, 0))
        assert len(flagged) == 1
        assert flagged[0].port == 8080

    def test_does_not_flag_when_inside_window(self):
        rule = AnomalyRule(port=8080, allowed_windows=[TimeWindow("00:00", "23:59")])
        ports = [_entry(8080)]
        assert detect_anomalies(ports, [rule], dt=datetime(2024, 1, 1, 12, 0)) == []

    def test_multiple_rules_independent(self):
        rules = [
            AnomalyRule(port=8080, allowed_windows=[TimeWindow("08:00", "18:00")]),
            AnomalyRule(port=9090, allowed_windows=[TimeWindow("08:00", "18:00")]),
        ]
        ports = [_entry(8080), _entry(9090), _entry(443)]
        flagged = detect_anomalies(ports, rules, dt=datetime(2024, 1, 1, 2, 0))
        assert {e.port for e in flagged} == {8080, 9090}
