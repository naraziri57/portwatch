"""Tests for portwatch.commands.audit_cmd."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.audit import append_events
from portwatch.commands.audit_cmd import cmd_audit_clear, cmd_audit_list
from portwatch.scanner import PortEntry


def _event(port: int = 8080) -> ChangeEvent:
    return ChangeEvent(kind="opened", entry=PortEntry(proto="tcp", port=port, process="svc"))


@pytest.fixture()
def audit_file(tmp_path: Path) -> Path:
    p = tmp_path / "audit.json"
    append_events(p, [_event(80), _event(443), _event(8080)])
    return p


def _args(audit_file, limit=50):
    return SimpleNamespace(audit_file=str(audit_file), limit=limit)


class TestCmdAuditList:
    def test_returns_zero(self, audit_file, capsys):
        rc = cmd_audit_list(_args(audit_file))
        assert rc == 0

    def test_prints_entries(self, audit_file, capsys):
        cmd_audit_list(_args(audit_file))
        out = capsys.readouterr().out
        assert "80" in out
        assert "443" in out

    def test_limit_restricts_output(self, audit_file, capsys):
        cmd_audit_list(_args(audit_file, limit=1))
        out = capsys.readouterr().out
        # only last entry shown
        assert out.count("opened") == 1

    def test_zero_limit_shows_all(self, audit_file, capsys):
        cmd_audit_list(_args(audit_file, limit=0))
        out = capsys.readouterr().out
        assert out.count("opened") == 3

    def test_missing_file_prints_message(self, tmp_path, capsys):
        args = _args(tmp_path / "nope.json")
        rc = cmd_audit_list(args)
        assert rc == 0
        assert "No audit entries" in capsys.readouterr().out


class TestCmdAuditClear:
    def test_returns_zero(self, audit_file, capsys):
        rc = cmd_audit_clear(_args(audit_file))
        assert rc == 0

    def test_file_removed(self, audit_file):
        cmd_audit_clear(_args(audit_file))
        assert not audit_file.exists()

    def test_prints_confirmation(self, audit_file, capsys):
        cmd_audit_clear(_args(audit_file))
        assert "cleared" in capsys.readouterr().out.lower()

    def test_missing_file_no_error(self, tmp_path, capsys):
        args = _args(tmp_path / "nope.json")
        rc = cmd_audit_clear(args)  # should not raise
        assert rc == 0
