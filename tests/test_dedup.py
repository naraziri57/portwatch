"""Tests for portwatch.dedup."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from portwatch.dedup import DedupWindow
from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent


def _entry(port: int = 8080, proto: str = "tcp", process: str = "nginx") -> PortEntry:
    return PortEntry(proto=proto, port=port, local_addr="0.0.0.0", state="LISTEN", process=process)


def _event(port: int = 8080, kind: str = "opened") -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port=port))


@pytest.fixture
def window() -> DedupWindow:
    return DedupWindow(window_seconds=60.0)


class TestDedupWindowValidation:
    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            DedupWindow(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            DedupWindow(window_seconds=-5)

    def test_valid_window_ok(self):
        w = DedupWindow(window_seconds=30)
        assert w.window_seconds == 30


class TestIsDuplicate:
    def test_first_event_not_duplicate(self, window):
        ev = _event()
        assert window.is_duplicate(ev) is False

    def test_after_record_is_duplicate(self, window):
        ev = _event()
        window.record(ev)
        assert window.is_duplicate(ev) is True

    def test_different_port_not_duplicate(self, window):
        window.record(_event(port=80))
        assert window.is_duplicate(_event(port=443)) is False

    def test_different_kind_not_duplicate(self, window):
        window.record(_event(port=80, kind="opened"))
        assert window.is_duplicate(_event(port=80, kind="closed")) is False

    def test_expired_entry_not_duplicate(self):
        w = DedupWindow(window_seconds=1.0)
        ev = _event()
        base = 1000.0
        with patch("portwatch.dedup.time.monotonic", return_value=base):
            w.record(ev)
        with patch("portwatch.dedup.time.monotonic", return_value=base + 2.0):
            assert w.is_duplicate(ev) is False


class TestFilterEvents:
    def test_empty_list_returns_empty(self, window):
        assert window.filter_events([]) == []

    def test_first_occurrence_passes_through(self, window):
        ev = _event()
        result = window.filter_events([ev])
        assert result == [ev]

    def test_duplicate_in_same_batch_suppressed(self, window):
        ev = _event()
        result = window.filter_events([ev, ev])
        assert len(result) == 1

    def test_unique_events_all_pass(self, window):
        events = [_event(port=80), _event(port=443), _event(port=8080)]
        result = window.filter_events(events)
        assert len(result) == 3

    def test_size_tracks_recorded_events(self, window):
        window.filter_events([_event(port=80), _event(port=443)])
        assert window.size == 2

    def test_clear_resets_state(self, window):
        window.record(_event())
        window.clear()
        assert window.size == 0
        assert window.is_duplicate(_event()) is False
