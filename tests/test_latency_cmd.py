"""Tests for portwatch.commands.latency_cmd."""
import argparse
from unittest.mock import patch, MagicMock

import pytest

from portwatch.commands.latency_cmd import cmd_latency, register_subcommands
from portwatch.scanner import PortEntry


def _entry(port=80, proto="tcp", address="127.0.0.1"):
    return PortEntry(port=port, proto=proto, address=address, process="nginx")


def _args(samples=1, timeout=0.5):
    ns = argparse.Namespace()
    ns.samples = samples
    ns.timeout = timeout
    return ns


def test_returns_one_on_scan_failure():
    with patch("portwatch.commands.latency_cmd.scan_ports", side_effect=RuntimeError("boom")):
        assert cmd_latency(_args()) == 1


def test_returns_zero_on_no_tcp_ports():
    udp_entry = _entry(port=53, proto="udp")
    with patch("portwatch.commands.latency_cmd.scan_ports", return_value=[udp_entry]):
        assert cmd_latency(_args()) == 0


def test_returns_zero_when_all_probes_fail():
    with patch("portwatch.commands.latency_cmd.scan_ports", return_value=[_entry()]):
        with patch("portwatch.commands.latency_cmd._probe_port", return_value=-1.0):
            assert cmd_latency(_args()) == 0


def test_returns_zero_on_successful_probe(capsys):
    with patch("portwatch.commands.latency_cmd.scan_ports", return_value=[_entry()]):
        with patch("portwatch.commands.latency_cmd._probe_port", return_value=3.5):
            rc = cmd_latency(_args(samples=2))
    assert rc == 0
    out = capsys.readouterr().out
    assert "80" in out


def test_output_contains_header(capsys):
    with patch("portwatch.commands.latency_cmd.scan_ports", return_value=[_entry()]):
        with patch("portwatch.commands.latency_cmd._probe_port", return_value=2.0):
            cmd_latency(_args())
    out = capsys.readouterr().out
    assert "PORT" in out
    assert "MEAN ms" in out


def test_register_adds_latency_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["latency"])
    assert hasattr(ns, "func")


def test_register_default_samples():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["latency"])
    assert ns.samples == 3


def test_register_custom_timeout():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["latency", "--timeout", "2.5"])
    assert ns.timeout == pytest.approx(2.5)
