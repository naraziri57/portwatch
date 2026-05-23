"""Tests for portwatch.commands.diff_cmd."""

import argparse
import json
import pytest

from portwatch.scanner import PortEntry
from portwatch.commands.diff_cmd import cmd_diff, register_subcommands


def _entry(port: int, proto: str = "tcp") -> PortEntry:
    return PortEntry(port=port, proto=proto, local_address="0.0.0.0", process=None)


def _write_snapshot(path, entries):
    data = [
        {"port": e.port, "proto": e.proto, "local_address": e.local_address, "process": e.process}
        for e in entries
    ]
    path.write_text(json.dumps(data))


@pytest.fixture()
def base_args(tmp_path):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    _write_snapshot(before, [_entry(80), _entry(443)])
    _write_snapshot(after, [_entry(80), _entry(443)])
    ns = argparse.Namespace(
        before=str(before),
        after=str(after),
        fail_on_change=False,
    )
    return ns


def test_no_change_returns_zero(base_args):
    assert cmd_diff(base_args) == 0


def test_no_change_message(base_args, capsys):
    cmd_diff(base_args)
    out = capsys.readouterr().out
    assert "No changes" in out


def test_opened_port_detected(base_args, tmp_path):
    after = tmp_path / "after2.json"
    _write_snapshot(after, [_entry(80), _entry(443), _entry(8080)])
    base_args.after = str(after)
    assert cmd_diff(base_args) == 0


def test_opened_port_in_output(base_args, tmp_path, capsys):
    after = tmp_path / "after2.json"
    _write_snapshot(after, [_entry(80), _entry(443), _entry(8080)])
    base_args.after = str(after)
    cmd_diff(base_args)
    out = capsys.readouterr().out
    assert "8080" in out


def test_fail_on_change_returns_one(base_args, tmp_path):
    after = tmp_path / "after3.json"
    _write_snapshot(after, [_entry(80)])
    base_args.after = str(after)
    base_args.fail_on_change = True
    assert cmd_diff(base_args) == 1


def test_missing_before_returns_one(base_args):
    base_args.before = "/nonexistent/path.json"
    assert cmd_diff(base_args) == 1


def test_missing_after_returns_one(base_args):
    base_args.after = "/nonexistent/path.json"
    assert cmd_diff(base_args) == 1


def test_register_adds_diff_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["diff", "a.json", "b.json"])
    assert ns.before == "a.json"
    assert ns.after == "b.json"


def test_register_fail_on_change_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["diff", "a.json", "b.json", "--fail-on-change"])
    assert ns.fail_on_change is True
