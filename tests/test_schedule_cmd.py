"""Tests for portwatch.commands.schedule_cmd."""

import argparse
import json
from pathlib import Path

import pytest

from portwatch.commands.schedule_cmd import (
    _load_schedule,
    _save_schedule,
    cmd_schedule_add,
    cmd_schedule_list,
    cmd_schedule_clear,
    _dispatch_schedule,
)
from portwatch.schedule import ScanSchedule


@pytest.fixture()
def sfile(tmp_path: Path) -> Path:
    return tmp_path / "sched.json"


def _args(sfile: Path, action: str = "list", **kwargs) -> argparse.Namespace:
    base = {"schedule_file": str(sfile), "schedule_action": action}
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_list_empty_schedule(sfile, capsys):
    rc = cmd_schedule_list(_args(sfile, "list"))
    assert rc == 0
    assert "No windows" in capsys.readouterr().out


def test_add_creates_file(sfile):
    rc = cmd_schedule_add(_args(sfile, "add", name="biz", start="08:00", end="18:00", days="0,1,2,3,4"))
    assert rc == 0
    assert sfile.exists()


def test_add_window_appears_in_list(sfile, capsys):
    cmd_schedule_add(_args(sfile, "add", name="biz", start="09:00", end="17:00", days=""))
    cmd_schedule_list(_args(sfile, "list"))
    out = capsys.readouterr().out
    assert "biz" in out
    assert "09:00" in out


def test_add_multiple_windows(sfile):
    cmd_schedule_add(_args(sfile, "add", name="a", start="08:00", end="12:00", days=""))
    cmd_schedule_add(_args(sfile, "add", name="b", start="13:00", end="17:00", days=""))
    schedule = _load_schedule(sfile)
    assert len(schedule.windows) == 2


def test_clear_removes_windows(sfile):
    cmd_schedule_add(_args(sfile, "add", name="x", start="08:00", end="18:00", days=""))
    rc = cmd_schedule_clear(_args(sfile, "clear"))
    assert rc == 0
    schedule = _load_schedule(sfile)
    assert schedule.windows == []


def test_dispatch_unknown_action_returns_one(sfile):
    rc = _dispatch_schedule(_args(sfile, None))
    assert rc == 1


def test_dispatch_list(sfile, capsys):
    rc = _dispatch_schedule(_args(sfile, "list"))
    assert rc == 0


def test_roundtrip_preserves_days(sfile):
    cmd_schedule_add(_args(sfile, "add", name="wkd", start="10:00", end="14:00", days="1,3"))
    schedule = _load_schedule(sfile)
    assert schedule.windows[0].days == [1, 3]
