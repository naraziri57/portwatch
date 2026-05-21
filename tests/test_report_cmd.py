"""Tests for portwatch.commands.report_cmd."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.report_cmd import cmd_report, register_subcommands
from portwatch.config import Config
from portwatch.scanner import PortEntry


@pytest.fixture()
def sample_ports():
    return [
        PortEntry(proto="tcp", port=22, state="LISTEN", process="sshd"),
        PortEntry(proto="tcp", port=80, state="LISTEN", process="nginx"),
    ]


@pytest.fixture()
def base_args(tmp_path):
    args = argparse.Namespace(config=None, diff_baseline=False)
    return args


def test_report_exits_zero_on_success(base_args, sample_ports):
    config = Config()
    with patch("portwatch.commands.report_cmd.scan_ports", return_value=sample_ports):
        with patch("portwatch.commands.report_cmd.print_report") as mock_print:
            code = cmd_report(base_args, config=config)
    assert code == 0
    mock_print.assert_called_once()


def test_report_passes_ports_to_print(base_args, sample_ports):
    config = Config()
    with patch("portwatch.commands.report_cmd.scan_ports", return_value=sample_ports):
        with patch("portwatch.commands.report_cmd.print_report") as mock_print:
            cmd_report(base_args, config=config)
    called_ports = mock_print.call_args[0][0]
    assert len(called_ports) == 2


def test_report_returns_1_on_scan_failure(base_args, capsys):
    config = Config()
    with patch(
        "portwatch.commands.report_cmd.scan_ports",
        side_effect=RuntimeError("no ss"),
    ):
        code = cmd_report(base_args, config=config)
    assert code == 1
    captured = capsys.readouterr()
    assert "scan failed" in captured.err


def test_report_diff_baseline_missing(tmp_path, capsys):
    args = argparse.Namespace(config=None, diff_baseline=True)
    config = Config(baseline_path=str(tmp_path / "baseline.json"))
    with patch("portwatch.commands.report_cmd.scan_ports", return_value=[]):
        code = cmd_report(args, config=config)
    assert code == 1
    captured = capsys.readouterr()
    assert "no baseline found" in captured.err


def test_report_diff_baseline_used(tmp_path, sample_ports):
    from portwatch.baseline import save_baseline

    bl_path = str(tmp_path / "baseline.json")
    save_baseline(sample_ports, bl_path)

    args = argparse.Namespace(config=None, diff_baseline=True)
    config = Config(baseline_path=bl_path)

    with patch("portwatch.commands.report_cmd.scan_ports", return_value=sample_ports):
        with patch("portwatch.commands.report_cmd.print_report") as mock_print:
            code = cmd_report(args, config=config)

    assert code == 0
    _, kwargs = mock_print.call_args
    assert kwargs.get("baseline") is not None


def test_register_subcommands_adds_report():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    parsed = parser.parse_args(["report"])
    assert hasattr(parsed, "func")
    assert parsed.func is cmd_report
