"""Unit tests for portwatch.timeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent
from portwatch.timeline import (
    TimelineEntry,
    append_events,
    load_timeline,
    query_range,
)


def _entry(port: int = 80, proto: str = "tcp", process: str = "nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


def _event(kind: str = "opened", port: int = 80) -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port=port))


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


class TestTimelineEntry:
    def test_to_dict_contains_required_keys(self):
        e = TimelineEntry(
            timestamp=_ts("2024-01-01T00:00:00"),
            kind="opened",
            port=443,
            proto="tcp",
            process="nginx",
        )
        d = e.to_dict()
        assert d["kind"] == "opened"
        assert d["port"] == 443
        assert d["proto"] == "tcp"
        assert d["process"] == "nginx"

    def test_from_dict_roundtrip(self):
        original = TimelineEntry(
            timestamp=_ts("2024-06-15T12:00:00"),
            kind="closed",
            port=22,
            proto="tcp",
            process="sshd",
        )
        assert TimelineEntry.from_dict(original.to_dict()).port == 22

    def test_from_event_sets_kind_and_port(self):
        ev = _event(kind="closed", port=8080)
        te = TimelineEntry.from_event(ev)
        assert te.kind == "closed"
        assert te.port == 8080

    def test_from_event_timestamp_is_utc(self):
        te = TimelineEntry.from_event(_event())
        assert te.timestamp.tzinfo is not None


def test_append_creates_file(tmp_path):
    p = tmp_path / "tl.json"
    append_events(p, [_event()])
    assert p.exists()


def test_append_accumulates(tmp_path):
    p = tmp_path / "tl.json"
    append_events(p, [_event(port=80)])
    append_events(p, [_event(port=443)])
    entries = load_timeline(p)
    assert len(entries) == 2


def test_load_empty_when_missing(tmp_path):
    assert load_timeline(tmp_path / "nope.json") == []


class TestQueryRange:
    def _make_entries(self):
        return [
            TimelineEntry(_ts("2024-01-01T10:00:00"), "opened", 80, "tcp"),
            TimelineEntry(_ts("2024-01-02T10:00:00"), "closed", 80, "tcp"),
            TimelineEntry(_ts("2024-01-03T10:00:00"), "opened", 443, "tcp"),
        ]

    def test_since_filters_older(self):
        result = query_range(self._make_entries(), since=_ts("2024-01-02T00:00:00"))
        assert len(result) == 2

    def test_until_filters_newer(self):
        result = query_range(self._make_entries(), until=_ts("2024-01-02T00:00:00"))
        assert len(result) == 1

    def test_no_bounds_returns_all(self):
        assert len(query_range(self._make_entries())) == 3
