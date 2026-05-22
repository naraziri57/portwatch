"""Tests for portwatch.commands.metrics_cmd."""
from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.metrics_cmd import cmd_metrics, register_subcommands
from portwatch.metrics import Metrics


def _args(**kwargs) -> Namespace:
    defaults = {"json": False, "scan": False}
    defaults.update(kwargs)
    return Namespace(**defaults)


@pytest.fixture(autouse=True)
def isolated_metrics(monkeypatch):
    """Each test gets a fresh Metrics instance."""
    fresh = Metrics()
    monkeypatch.setattr("portwatch.commands.metrics_cmd.get_metrics", lambda: fresh)
    return fresh


def test_returns_zero(isolated_metrics, capsys):
    assert cmd_metrics(_args()) == 0


def test_plain_output_contains_scans_label(isolated_metrics, capsys):
    cmd_metrics(_args())
    out = capsys.readouterr().out
    assert "scans_total" in out


def test_plain_output_no_events_message(isolated_metrics, capsys):
    cmd_metrics(_args())
    out = capsys.readouterr().out
    assert "no events recorded" in out


def test_json_flag_produces_valid_json(isolated_metrics, capsys):
    cmd_metrics(_args(json=True))
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "scans_total" in data
    assert "events_by_kind" in data


def test_scan_flag_calls_scan_ports(isolated_metrics):
    fake_ports = []
    with patch("portwatch.commands.metrics_cmd.scan_ports", return_value=fake_ports) as mock_scan:
        cmd_metrics(_args(scan=True))
    mock_scan.assert_called_once()


def test_scan_flag_increments_scan_counter(isolated_metrics):
    with patch("portwatch.commands.metrics_cmd.scan_ports", return_value=[]):
        cmd_metrics(_args(scan=True))
    assert isolated_metrics.scans_total == 1


def test_scan_error_increments_error_counter(isolated_metrics, capsys):
    with patch("portwatch.commands.metrics_cmd.scan_ports", side_effect=RuntimeError("boom")):
        result = cmd_metrics(_args(scan=True))
    assert result == 0  # still exits cleanly
    assert isolated_metrics.scan_errors == 1


def test_register_subcommands_adds_metrics():
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    args = parser.parse_args(["metrics"])
    assert hasattr(args, "func")
