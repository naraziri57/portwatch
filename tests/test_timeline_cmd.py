"""Tests for portwatch.commands.timeline_cmd."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from portwatch.timeline import TimelineEntry, append_events
from portwatch.commands.timeline_cmd import cmd_timeline
from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent


def _entry(port=80):
    return PortEntry(port=port, proto="tcp", address="0.0.0.0", process="nginx")


def _event(kind="opened", port=80):
    return ChangeEvent(kind=kind, entry=_entry(port=port))


def _args(**kwargs) -> argparse.Namespace:
    defaults = {"since": None, "until": None, "kind": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_returns_zero_on_empty(tmp_path):
    p = tmp_path / "tl.json"
    assert cmd_timeline(_args(), timeline_path=p) == 0


def test_prints_entries(tmp_path, capsys):
    p = tmp_path / "tl.json"
    append_events(p, [_event(kind="opened", port=22)])
    cmd_timeline(_args(), timeline_path=p)
    out = capsys.readouterr().out
    assert "opened" in out
    assert "22" in out


def test_kind_filter(tmp_path, capsys):
    p = tmp_path / "tl.json"
    append_events(p, [_event(kind="opened", port=80), _event(kind="closed", port=443)])
    cmd_timeline(_args(kind="closed"), timeline_path=p)
    out = capsys.readouterr().out
    assert "closed" in out
    assert "opened" not in out


def test_invalid_since_returns_one(tmp_path):
    p = tmp_path / "tl.json"
    assert cmd_timeline(_args(since="not-a-date"), timeline_path=p) == 1


def test_since_filters_old_entries(tmp_path, capsys):
    p = tmp_path / "tl.json"
    old = TimelineEntry(
        timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        kind="opened",
        port=9999,
        proto="tcp",
    )
    recent = TimelineEntry(
        timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
        kind="opened",
        port=8080,
        proto="tcp",
    )
    p.write_text(json.dumps([old.to_dict(), recent.to_dict()]))
    cmd_timeline(_args(since="2024-01-01T00:00:00"), timeline_path=p)
    out = capsys.readouterr().out
    assert "8080" in out
    assert "9999" not in out


def test_no_entries_message(tmp_path, capsys):
    p = tmp_path / "tl.json"
    cmd_timeline(_args(), timeline_path=p)
    assert "No timeline entries" in capsys.readouterr().out
