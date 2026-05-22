"""Tests for portwatch.commands.escalation_cmd."""
import argparse
import pytest
from unittest.mock import patch, MagicMock

from portwatch.commands.escalation_cmd import (
    cmd_escalation_status,
    register_subcommands,
    _dispatch_escalation,
)
from portwatch.scanner import PortEntry


@pytest.fixture()
def base_args():
    ns = argparse.Namespace()
    ns.escalate_after = 300.0
    ns.max_escalations = 3
    return ns


_PORTS = [
    PortEntry(proto="tcp", port=80, pid=None, process=None),
    PortEntry(proto="tcp", port=443, pid=None, process=None),
]


def test_status_exits_zero_on_success(base_args, capsys):
    with patch("portwatch.commands.escalation_cmd.scan_ports", return_value=_PORTS):
        rc = cmd_escalation_status(base_args)
    assert rc == 0


def test_status_prints_tracked_ports(base_args, capsys):
    with patch("portwatch.commands.escalation_cmd.scan_ports", return_value=_PORTS):
        cmd_escalation_status(base_args)
    out = capsys.readouterr().out
    assert "tcp:80" in out
    assert "tcp:443" in out


def test_status_empty_ports(base_args, capsys):
    with patch("portwatch.commands.escalation_cmd.scan_ports", return_value=[]):
        rc = cmd_escalation_status(base_args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "No open ports" in out


def test_status_returns_1_on_scan_failure(base_args):
    with patch(
        "portwatch.commands.escalation_cmd.scan_ports",
        side_effect=RuntimeError("oops"),
    ):
        rc = cmd_escalation_status(base_args)
    assert rc == 1


def test_dispatch_without_subcommand_returns_1():
    args = argparse.Namespace(escalation_cmd=None)
    assert _dispatch_escalation(args) == 1


def test_register_creates_escalation_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_subcommands(sub)
    ns = parser.parse_args(["escalation", "status"])
    assert ns.cmd == "escalation"
