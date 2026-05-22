"""Tests for portwatch.audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.audit import (
    AuditEntry,
    append_events,
    clear_audit,
    load_audit,
)
from portwatch.scanner import PortEntry


@pytest.fixture()
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "audit.json"


def _event(kind: str = "opened", port: int = 8080) -> ChangeEvent:
    entry = PortEntry(proto="tcp", port=port, process="python")
    return ChangeEvent(kind=kind, entry=entry)


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

class TestAuditEntry:
    def test_from_event_sets_kind(self):
        e = AuditEntry.from_event(_event("closed", 443))
        assert e.kind == "closed"

    def test_from_event_sets_port(self):
        e = AuditEntry.from_event(_event(port=9000))
        assert e.port == 9000

    def test_from_event_sets_process(self):
        e = AuditEntry.from_event(_event())
        assert e.process == "python"

    def test_roundtrip_dict(self):
        e = AuditEntry.from_event(_event())
        assert AuditEntry.from_dict(e.to_dict()) == e

    def test_timestamp_is_string(self):
        e = AuditEntry.from_event(_event())
        assert isinstance(e.timestamp, str)


# ---------------------------------------------------------------------------
# append_events / load_audit
# ---------------------------------------------------------------------------

class TestAppendEvents:
    def test_creates_file(self, audit_path):
        append_events(audit_path, [_event()])
        assert audit_path.exists()

    def test_file_is_valid_json(self, audit_path):
        append_events(audit_path, [_event()])
        with audit_path.open() as fh:
            data = json.load(fh)
        assert isinstance(data, list)

    def test_single_event_stored(self, audit_path):
        append_events(audit_path, [_event(port=1234)])
        entries = load_audit(audit_path)
        assert len(entries) == 1
        assert entries[0].port == 1234

    def test_multiple_appends_accumulate(self, audit_path):
        append_events(audit_path, [_event(port=80)])
        append_events(audit_path, [_event(port=443)])
        entries = load_audit(audit_path)
        assert len(entries) == 2

    def test_max_entries_trim(self, audit_path):
        events = [_event(port=i) for i in range(10)]
        append_events(audit_path, events, max_entries=5)
        entries = load_audit(audit_path)
        assert len(entries) == 5
        # most recent 5 kept
        assert entries[-1].port == 9

    def test_load_missing_file_returns_empty(self, audit_path):
        assert load_audit(audit_path) == []

    def test_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "audit.json"
        append_events(nested, [_event()])
        assert nested.exists()


# ---------------------------------------------------------------------------
# clear_audit
# ---------------------------------------------------------------------------

class TestClearAudit:
    def test_removes_file(self, audit_path):
        append_events(audit_path, [_event()])
        clear_audit(audit_path)
        assert not audit_path.exists()

    def test_no_error_if_missing(self, audit_path):
        clear_audit(audit_path)  # should not raise
