"""Tests for portwatch.replay."""
from __future__ import annotations

import pytest

from portwatch.audit import AuditEntry
from portwatch.alerter import ChangeEvent
from portwatch.replay import ReplayOptions, ReplayResult, replay_entries, _entry_to_event


TS = "2024-01-01T00:00:00"


def _ae(kind: str, port: int) -> AuditEntry:
    return AuditEntry(kind=kind, port=port, proto="tcp", address="0.0.0.0", process=None, timestamp=TS)


# ---------------------------------------------------------------------------
# ReplayOptions validation
# ---------------------------------------------------------------------------

class TestReplayOptionsValidation:
    def test_default_speed(self):
        assert ReplayOptions().speed == 1.0

    def test_negative_speed_raises(self):
        with pytest.raises(ValueError, match="speed"):
            ReplayOptions(speed=-0.1)

    def test_negative_start_raises(self):
        with pytest.raises(ValueError, match="start_index"):
            ReplayOptions(start_index=-1)

    def test_zero_speed_ok(self):
        opts = ReplayOptions(speed=0)
        assert opts.speed == 0


# ---------------------------------------------------------------------------
# _entry_to_event
# ---------------------------------------------------------------------------

def test_entry_to_event_preserves_kind():
    ae = _ae("opened", 8080)
    ev = _entry_to_event(ae)
    assert ev.kind == "opened"


def test_entry_to_event_preserves_port():
    ae = _ae("closed", 443)
    ev = _entry_to_event(ae)
    assert ev.port == 443


# ---------------------------------------------------------------------------
# replay_entries
# ---------------------------------------------------------------------------

class TestReplayEntries:
    def _collect(self, entries, options=None):
        received: list[ChangeEvent] = []
        result = replay_entries(entries, received.append, options)
        return result, received

    def test_all_entries_replayed_by_default(self):
        entries = [_ae("opened", 80), _ae("closed", 80)]
        result, received = self._collect(entries)
        assert result.replayed == 2
        assert len(received) == 2

    def test_skipped_count_with_filter(self):
        entries = [_ae("opened", 80), _ae("closed", 80), _ae("opened", 443)]
        opts = ReplayOptions(filter_kind="opened")
        result, received = self._collect(entries, opts)
        assert result.replayed == 2
        assert result.skipped == 1

    def test_filter_closed_only(self):
        entries = [_ae("opened", 80), _ae("closed", 80)]
        opts = ReplayOptions(filter_kind="closed")
        result, received = self._collect(entries, opts)
        assert result.replayed == 1
        assert received[0].kind == "closed"

    def test_start_index_slices_entries(self):
        entries = [_ae("opened", 80), _ae("opened", 443), _ae("opened", 8080)]
        opts = ReplayOptions(start_index=1)
        result, received = self._collect(entries, opts)
        assert result.replayed == 2
        assert received[0].port == 443

    def test_end_index_slices_entries(self):
        entries = [_ae("opened", 80), _ae("opened", 443), _ae("opened", 8080)]
        opts = ReplayOptions(end_index=2)
        result, received = self._collect(entries, opts)
        assert result.replayed == 2
        assert received[-1].port == 443

    def test_empty_entries_returns_zero(self):
        result, received = self._collect([])
        assert result.replayed == 0
        assert result.skipped == 0

    def test_events_stored_in_result(self):
        entries = [_ae("opened", 22)]
        result, _ = self._collect(entries)
        assert len(result.events) == 1
        assert result.events[0].port == 22
