"""Tests for portwatch.digest and the digest CLI command."""

from __future__ import annotations

import argparse
import datetime
from unittest.mock import MagicMock, patch

import pytest

from portwatch.digest import DigestReport, build_digest
from portwatch.alerter import ChangeEvent


def _ev(kind: str = "opened", port: int = 8080, proto: str = "tcp", process: str = "nginx") -> ChangeEvent:
    return ChangeEvent(kind=kind, port=port, proto=proto, process=process)


class TestDigestReport:
    def test_empty_by_default(self):
        r = DigestReport()
        assert r.is_empty

    def test_add_increases_count(self):
        r = DigestReport()
        r.add(_ev())
        assert len(r.events) == 1
        assert not r.is_empty

    def test_summary_empty(self):
        r = DigestReport()
        assert r.summary() == "No changes detected."

    def test_summary_contains_total(self):
        r = build_digest([_ev(), _ev(kind="closed", port=9090)])
        s = r.summary()
        assert "Total changes: 2" in s

    def test_summary_contains_kinds(self):
        r = build_digest([_ev(kind="opened"), _ev(kind="opened"), _ev(kind="closed")])
        s = r.summary()
        assert "opened: 2" in s
        assert "closed: 1" in s

    def test_summary_contains_timestamp(self):
        fixed = datetime.datetime(2024, 6, 1, 12, 0, 0)
        r = DigestReport(generated_at=fixed)
        r.add(_ev())
        assert "2024-06-01 12:00:00" in r.summary()

    def test_reset_clears_events(self):
        r = build_digest([_ev(), _ev()])
        r.reset()
        assert r.is_empty

    def test_build_digest_convenience(self):
        events = [_ev(port=i) for i in range(5)]
        r = build_digest(events)
        assert len(r.events) == 5


class TestDigestCmd:
    def _args(self, audit_file: str, limit: int = 0) -> argparse.Namespace:
        return argparse.Namespace(audit_file=audit_file, limit=limit)

    def test_returns_one_when_file_missing(self, tmp_path):
        from portwatch.commands.digest_cmd import cmd_digest
        args = self._args(str(tmp_path / "no_such.jsonl"))
        assert cmd_digest(args) == 1

    def test_returns_zero_on_success(self, tmp_path):
        from portwatch.commands.digest_cmd import cmd_digest
        from portwatch.audit import append_events
        audit_file = tmp_path / "audit.jsonl"
        ev = ChangeEvent(kind="opened", port=22, proto="tcp", process="sshd")
        append_events(audit_file, [ev])
        args = self._args(str(audit_file))
        assert cmd_digest(args) == 0

    def test_limit_restricts_entries(self, tmp_path, capsys):
        from portwatch.commands.digest_cmd import cmd_digest
        from portwatch.audit import append_events
        audit_file = tmp_path / "audit.jsonl"
        events = [ChangeEvent(kind="opened", port=p, proto="tcp", process="x") for p in range(10)]
        append_events(audit_file, events)
        args = self._args(str(audit_file), limit=3)
        rc = cmd_digest(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Total changes: 3" in out
