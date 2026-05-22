"""Tests for portwatch.commands.trends_cmd."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.trends_cmd import cmd_trends, register_subcommands
from portwatch.trends import PortTrend


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        audit_file="portwatch_audit.jsonl",
        window=60,
        threshold=3,
        flapping_only=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# cmd_trends
# ---------------------------------------------------------------------------

class TestCmdTrends:
    def test_returns_zero_on_success(self, capsys):
        with patch(
            "portwatch.commands.trends_cmd._build_tracker_from_audit"
        ) as mock_build:
            mock_build.return_value = MagicMock(all_trends=lambda: [], flapping_ports=lambda threshold: [])
            rc = cmd_trends(_args())
        assert rc == 0

    def test_no_trends_prints_none(self, capsys):
        with patch(
            "portwatch.commands.trends_cmd._build_tracker_from_audit"
        ) as mock_build:
            mock_build.return_value = MagicMock(all_trends=lambda: [], flapping_ports=lambda threshold: [])
            cmd_trends(_args())
        out = capsys.readouterr().out
        assert "none" in out.lower()

    def test_all_trends_listed(self, capsys):
        trend = PortTrend(port=8080, proto="tcp", opens=1, closes=0)
        tracker_mock = MagicMock()
        tracker_mock.all_trends.return_value = [trend]
        with patch(
            "portwatch.commands.trends_cmd._build_tracker_from_audit",
            return_value=tracker_mock,
        ):
            cmd_trends(_args(flapping_only=False))
        out = capsys.readouterr().out
        assert "8080" in out

    def test_flapping_only_flag(self, capsys):
        trend = PortTrend(port=9090, proto="tcp", opens=5, closes=5)
        tracker_mock = MagicMock()
        tracker_mock.flapping_ports.return_value = [trend]
        with patch(
            "portwatch.commands.trends_cmd._build_tracker_from_audit",
            return_value=tracker_mock,
        ):
            cmd_trends(_args(flapping_only=True))
        out = capsys.readouterr().out
        assert "9090" in out
        assert "FLAPPING" in out

    def test_missing_audit_file_returns_zero(self, tmp_path, capsys):
        rc = cmd_trends(_args(audit_file=str(tmp_path / "nonexistent.jsonl")))
        assert rc == 0


# ---------------------------------------------------------------------------
# register_subcommands
# ---------------------------------------------------------------------------

def test_register_adds_trends_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["trends"])
    assert hasattr(ns, "func")


def test_register_window_default():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["trends"])
    assert ns.window == 60


def test_register_threshold_custom():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["trends", "--threshold", "5"])
    assert ns.threshold == 5
