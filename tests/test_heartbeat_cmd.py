"""Tests for portwatch.commands.heartbeat_cmd."""

from __future__ import annotations

import argparse
import json

import pytest

import portwatch.commands.heartbeat_cmd as hcmd
from portwatch.heartbeat import Heartbeat, HeartbeatConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(**kwargs) -> argparse.Namespace:
    defaults = {"json": False, "heartbeat_action": "status"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture(autouse=True)
def fresh_heartbeat(monkeypatch):
    """Replace the module-level heartbeat with a fresh one for each test."""
    hb = Heartbeat(HeartbeatConfig(interval=60.0))
    monkeypatch.setattr(hcmd, "_heartbeat", hb)
    return hb


# ---------------------------------------------------------------------------
# cmd_heartbeat_status
# ---------------------------------------------------------------------------

class TestCmdHeartbeatStatus:
    def test_returns_zero(self, capsys):
        rc = hcmd.cmd_heartbeat_status(_args())
        assert rc == 0

    def test_plain_output_contains_beats(self, capsys):
        hcmd.cmd_heartbeat_status(_args())
        out = capsys.readouterr().out
        assert "beats" in out

    def test_plain_output_contains_uptime(self, capsys):
        hcmd.cmd_heartbeat_status(_args())
        out = capsys.readouterr().out
        assert "uptime" in out

    def test_json_flag_produces_valid_json(self, capsys):
        hcmd.cmd_heartbeat_status(_args(json=True))
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "beats" in data
        assert "uptime_seconds" in data

    def test_json_beats_initially_zero(self, capsys):
        hcmd.cmd_heartbeat_status(_args(json=True))
        data = json.loads(capsys.readouterr().out)
        assert data["beats"] == 0


# ---------------------------------------------------------------------------
# cmd_heartbeat_reset
# ---------------------------------------------------------------------------

class TestCmdHeartbeatReset:
    def test_returns_zero(self, capsys):
        rc = hcmd.cmd_heartbeat_reset(_args())
        assert rc == 0

    def test_reset_clears_beats(self, fresh_heartbeat):
        fresh_heartbeat.force_beat()
        assert fresh_heartbeat.state.beats == 1
        hcmd.cmd_heartbeat_reset(_args())
        assert hcmd.get_heartbeat().state.beats == 0


# ---------------------------------------------------------------------------
# cmd_heartbeat_ping
# ---------------------------------------------------------------------------

class TestCmdHeartbeatPing:
    def test_returns_zero(self, capsys):
        rc = hcmd.cmd_heartbeat_ping(_args())
        assert rc == 0

    def test_ping_increments_beats(self, fresh_heartbeat):
        hcmd.cmd_heartbeat_ping(_args())
        assert hcmd.get_heartbeat().state.beats == 1

    def test_multiple_pings_accumulate(self, capsys):
        hcmd.cmd_heartbeat_ping(_args())
        hcmd.cmd_heartbeat_ping(_args())
        assert hcmd.get_heartbeat().state.beats == 2


# ---------------------------------------------------------------------------
# _dispatch_heartbeat
# ---------------------------------------------------------------------------

class TestDispatchHeartbeat:
    def test_unknown_action_returns_one(self, capsys):
        rc = hcmd._dispatch_heartbeat(_args(heartbeat_action="nope"))
        assert rc == 1

    def test_status_action_dispatched(self, capsys):
        rc = hcmd._dispatch_heartbeat(_args(heartbeat_action="status"))
        assert rc == 0

    def test_ping_action_dispatched(self, capsys):
        rc = hcmd._dispatch_heartbeat(_args(heartbeat_action="ping"))
        assert rc == 0
