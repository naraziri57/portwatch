"""Integration tests: replay entries end-to-end via the audit module."""
from __future__ import annotations

import pathlib
from typing import List

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.audit import AuditEntry, append_events
from portwatch.replay import ReplayOptions, replay_entries


TS = "2024-01-01T12:00:00"


def _make_event(kind: str, port: int) -> ChangeEvent:
    return ChangeEvent(kind=kind, port=port)


@pytest.fixture()
def audit_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "audit.jsonl"


class TestReplayIntegration:
    def _load_and_replay(
        self,
        audit_path: pathlib.Path,
        options: ReplayOptions | None = None,
    ) -> List[ChangeEvent]:
        from portwatch.audit import load_audit
        entries = load_audit(audit_path)
        received: List[ChangeEvent] = []
        replay_entries(entries, received.append, options)
        return received

    def test_full_roundtrip(self, audit_path):
        events = [_make_event("opened", 80), _make_event("closed", 80)]
        append_events(audit_path, events)
        received = self._load_and_replay(audit_path)
        assert len(received) == 2
        assert received[0].kind == "opened"
        assert received[1].kind == "closed"

    def test_filter_reduces_output(self, audit_path):
        events = [_make_event("opened", 80), _make_event("opened", 443),
                  _make_event("closed", 80)]
        append_events(audit_path, events)
        opts = ReplayOptions(filter_kind="opened")
        received = self._load_and_replay(audit_path, opts)
        assert all(e.kind == "opened" for e in received)
        assert len(received) == 2

    def test_window_slicing(self, audit_path):
        events = [_make_event("opened", p) for p in [80, 443, 8080, 9090]]
        append_events(audit_path, events)
        opts = ReplayOptions(start_index=1, end_index=3)
        received = self._load_and_replay(audit_path, opts)
        assert len(received) == 2
        assert received[0].port == 443
        assert received[1].port == 8080

    def test_empty_audit_file_no_crash(self, audit_path):
        audit_path.touch()
        received = self._load_and_replay(audit_path)
        assert received == []
