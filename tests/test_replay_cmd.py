"""Tests for portwatch.commands.replay_cmd."""
from __future__ import annotations

import argparse
import json
import pathlib

import pytest

from portwatch.commands.replay_cmd import cmd_replay, register_subcommands


TS = "2024-01-01T00:00:00"


def _write_audit(path: pathlib.Path, entries: list) -> None:
    with path.open("w") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


@pytest.fixture()
def audit_file(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "audit.jsonl"
    _write_audit(p, [
        {"kind": "opened", "port": 80, "proto": "tcp",
         "address": "0.0.0.0", "process": None, "timestamp": TS},
        {"kind": "closed", "port": 80, "proto": "tcp",
         "address": "0.0.0.0", "process": None, "timestamp": TS},
    ])
    return p


def _args(audit_file, **kwargs) -> argparse.Namespace:
    defaults = dict(
        audit_file=str(audit_file),
        kind=None,
        start=0,
        end=None,
        stderr=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_returns_zero_on_success(audit_file):
    assert cmd_replay(_args(audit_file)) == 0


def test_returns_one_on_missing_file(tmp_path):
    args = _args(tmp_path / "nonexistent.jsonl")
    assert cmd_replay(args) == 1


def test_filter_kind_opened(audit_file):
    args = _args(audit_file, kind="opened")
    assert cmd_replay(args) == 0


def test_filter_kind_closed(audit_file):
    args = _args(audit_file, kind="closed")
    assert cmd_replay(args) == 0


def test_start_index_respected(audit_file):
    args = _args(audit_file, start=1)
    assert cmd_replay(args) == 0


def test_end_index_respected(audit_file):
    args = _args(audit_file, end=1)
    assert cmd_replay(args) == 0


def test_register_adds_replay_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["replay", "/tmp/audit.jsonl"])
    assert ns.audit_file == "/tmp/audit.jsonl"


def test_register_sets_func():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["replay", "/tmp/x.jsonl"])
    assert ns.func is cmd_replay
