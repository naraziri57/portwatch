"""Tests for portwatch.commands.bandwidth_cmd."""
import argparse
import pytest
from unittest.mock import patch, MagicMock

from portwatch.commands.bandwidth_cmd import cmd_bandwidth, register_subcommands
from portwatch.scanner import PortEntry


def _entry(port=80, proto="tcp", addr="0.0.0.0", process="nginx"):
    return PortEntry(port=port, proto=proto, local_address=addr, process=process)


def _args(**kwargs):
    ns = argparse.Namespace(bytes_in=0, bytes_out=0)
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


class TestCmdBandwidth:
    def test_returns_zero_on_success(self):
        with patch("portwatch.commands.bandwidth_cmd.scan_ports", return_value=[_entry()]):
            assert cmd_bandwidth(_args()) == 0

    def test_returns_one_on_scan_failure(self):
        with patch(
            "portwatch.commands.bandwidth_cmd.scan_ports",
            side_effect=RuntimeError("boom"),
        ):
            assert cmd_bandwidth(_args()) == 1

    def test_empty_ports_prints_message(self, capsys):
        with patch("portwatch.commands.bandwidth_cmd.scan_ports", return_value=[]):
            cmd_bandwidth(_args())
        out = capsys.readouterr().out
        assert "No open ports" in out

    def test_output_contains_port(self, capsys):
        with patch(
            "portwatch.commands.bandwidth_cmd.scan_ports",
            return_value=[_entry(port=8080)],
        ):
            cmd_bandwidth(_args(bytes_in=100, bytes_out=200))
        out = capsys.readouterr().out
        assert "8080" in out

    def test_output_contains_summary_label(self, capsys):
        with patch(
            "portwatch.commands.bandwidth_cmd.scan_ports",
            return_value=[_entry(port=443, proto="tcp")],
        ):
            cmd_bandwidth(_args())
        out = capsys.readouterr().out
        assert "Bandwidth summary" in out

    def test_bytes_in_out_recorded(self, capsys):
        with patch(
            "portwatch.commands.bandwidth_cmd.scan_ports",
            return_value=[_entry(port=22)],
        ):
            cmd_bandwidth(_args(bytes_in=512, bytes_out=256))
        out = capsys.readouterr().out
        # total bytes = 512+256 = 768
        assert "768B" in out


class TestRegisterSubcommands:
    def test_bandwidth_subcommand_present(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_subcommands(sub)
        args = parser.parse_args(["bandwidth"])
        assert hasattr(args, "func")

    def test_default_bytes_in_is_zero(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_subcommands(sub)
        args = parser.parse_args(["bandwidth"])
        assert args.bytes_in == 0

    def test_custom_bytes_accepted(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_subcommands(sub)
        args = parser.parse_args(["bandwidth", "--bytes-in", "1024", "--bytes-out", "2048"])
        assert args.bytes_in == 1024
        assert args.bytes_out == 2048
