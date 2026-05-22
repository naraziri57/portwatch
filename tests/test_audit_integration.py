"""Integration: watcher emits events → audit log is updated."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.audit import append_events, load_audit
from portwatch.scanner import PortEntry


def _make_event(kind: str, port: int) -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=PortEntry(proto="tcp", port=port, process="test"))


class TestAuditRoundtrip:
    """Simulate the watcher writing events and the CLI reading them back."""

    def test_events_persist_across_calls(self, tmp_path):
        log = tmp_path / "audit.json"
        append_events(log, [_make_event("opened", 80)])
        append_events(log, [_make_event("closed", 80)])
        entries = load_audit(log)
        assert len(entries) == 2
        assert entries[0].kind == "opened"
        assert entries[1].kind == "closed"

    def test_trim_keeps_newest(self, tmp_path):
        log = tmp_path / "audit.json"
        for port in range(20):
            append_events(log, [_make_event("opened", port)], max_entries=10)
        entries = load_audit(log)
        assert len(entries) == 10
        assert entries[-1].port == 19

    def test_no_events_does_not_corrupt_log(self, tmp_path):
        log = tmp_path / "audit.json"
        append_events(log, [_make_event("opened", 443)])
        append_events(log, [])  # empty batch
        entries = load_audit(log)
        assert len(entries) == 1

    def test_entry_fields_preserved(self, tmp_path):
        log = tmp_path / "audit.json"
        ev = _make_event("opened", 9999)
        append_events(log, [ev])
        entry = load_audit(log)[0]
        assert entry.proto == "tcp"
        assert entry.port == 9999
        assert entry.process == "test"
        assert entry.kind == "opened"
