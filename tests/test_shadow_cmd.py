"""Tests for portwatch.commands.shadow_cmd."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.shadow_cmd import cmd_shadow, register_subcommands
from portwatch.scanner import PortEntry
from portwatch.shadow import ShadowPort


def _entry(port: int = 9000, address: str = "127.0.0.1") -> PortEntry:
    return PortEntry(port=port, proto="tcp", address=address, process="test")


def _args(**kwargs) -> argparse.Namespace:
    defaults = {"fail_on_found": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCmdShadow:
    def test_returns_zero_no_shadows(self, capsys):
        with patch("portwatch.commands.shadow_cmd.scan_ports", return_value=[_entry(address="0.0.0.0")]):
            rc = cmd_shadow(_args())
        assert rc == 0
        out = capsys.readouterr().out
        assert "No shadow" in out

    def test_returns_zero_with_shadows_no_fail_flag(self, capsys):
        with patch("portwatch.commands.shadow_cmd.scan_ports", return_value=[_entry(address="127.0.0.1")]):
            rc = cmd_shadow(_args(fail_on_found=False))
        assert rc == 0

    def test_returns_two_with_fail_flag(self):
        with patch("portwatch.commands.shadow_cmd.scan_ports", return_value=[_entry(address="127.0.0.1")]):
            rc = cmd_shadow(_args(fail_on_found=True))
        assert rc == 2

    def test_returns_one_on_scan_failure(self, capsys):
        with patch("portwatch.commands.shadow_cmd.scan_ports", side_effect=RuntimeError("boom")):
            rc = cmd_shadow(_args())
        assert rc == 1
        assert "scan failed" in capsys.readouterr().err

    def test_prints_shadow_count(self, capsys):
        ports = [_entry(port=p, address="127.0.0.1") for p in (3306, 5432)]
        with patch("portwatch.commands.shadow_cmd.scan_ports", return_value=ports):
            cmd_shadow(_args())
        out = capsys.readouterr().out
        assert "2 shadow port" in out

    def test_register_adds_shadow_subcommand(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_subcommands(sub)
        args = parser.parse_args(["shadow"])
        assert hasattr(args, "func")
        assert args.func is cmd_shadow

    def test_register_fail_on_found_flag(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_subcommands(sub)
        args = parser.parse_args(["shadow", "--fail-on-found"])
        assert args.fail_on_found is True
