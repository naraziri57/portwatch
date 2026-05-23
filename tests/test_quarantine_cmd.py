"""Tests for quarantine_cmd subcommands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from portwatch.commands.quarantine_cmd import (
    cmd_quarantine_add,
    cmd_quarantine_list,
    cmd_quarantine_remove,
    _dispatch_quarantine,
)


@pytest.fixture()
def qfile(tmp_path: Path) -> Path:
    return tmp_path / "quarantine.json"


def _args(qfile: Path, **kwargs) -> argparse.Namespace:
    defaults = dict(
        quarantine_file=str(qfile),
        port=8080,
        proto="tcp",
        reason="test",
        duration=3600,
        quarantine_action=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCmdQuarantineAdd:
    def test_returns_zero_on_success(self, qfile):
        assert cmd_quarantine_add(_args(qfile)) == 0

    def test_creates_file(self, qfile):
        cmd_quarantine_add(_args(qfile))
        assert qfile.exists()

    def test_file_contains_entry(self, qfile):
        cmd_quarantine_add(_args(qfile, port=9000, proto="udp"))
        data = json.loads(qfile.read_text())
        assert any(e["port"] == 9000 and e["proto"] == "udp" for e in data)

    def test_second_add_does_not_duplicate(self, qfile):
        cmd_quarantine_add(_args(qfile, port=443))
        cmd_quarantine_add(_args(qfile, port=443))
        data = json.loads(qfile.read_text())
        matching = [e for e in data if e["port"] == 443]
        assert len(matching) == 1


class TestCmdQuarantineRemove:
    def test_returns_one_if_no_file(self, qfile):
        assert cmd_quarantine_remove(_args(qfile)) == 1

    def test_returns_zero_after_add(self, qfile):
        cmd_quarantine_add(_args(qfile, port=8080))
        assert cmd_quarantine_remove(_args(qfile, port=8080)) == 0

    def test_entry_gone_after_remove(self, qfile):
        cmd_quarantine_add(_args(qfile, port=8080))
        cmd_quarantine_remove(_args(qfile, port=8080))
        data = json.loads(qfile.read_text())
        assert not any(e["port"] == 8080 for e in data)


class TestCmdQuarantineList:
    def test_returns_zero_no_file(self, qfile, capsys):
        assert cmd_quarantine_list(_args(qfile)) == 0

    def test_prints_no_entries_message(self, qfile, capsys):
        cmd_quarantine_list(_args(qfile))
        out = capsys.readouterr().out
        assert "No quarantine file" in out

    def test_lists_added_entry(self, qfile, capsys):
        cmd_quarantine_add(_args(qfile, port=8080, reason="suspicious"))
        cmd_quarantine_list(_args(qfile))
        out = capsys.readouterr().out
        assert "8080" in out


def test_dispatch_no_action_returns_one(qfile):
    args = _args(qfile, quarantine_action=None)
    assert _dispatch_quarantine(args) == 1


def test_dispatch_add_routes_correctly(qfile):
    args = _args(qfile, quarantine_action="add")
    assert _dispatch_quarantine(args) == 0
