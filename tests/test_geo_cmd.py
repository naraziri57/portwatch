"""Tests for portwatch.commands.geo_cmd."""
from __future__ import annotations

import argparse
import types
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.geo_cmd import cmd_geo, register_subcommands, _unique_ips
from portwatch.scanner import PortEntry


def _entry(local_address: str = "192.168.1.5:8080") -> PortEntry:
    return PortEntry(
        protocol="tcp",
        local_address=local_address,
        state="LISTEN",
        pid=None,
        process=None,
    )


def _args(**kwargs) -> argparse.Namespace:
    defaults = {"db": None, "resolve": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# _unique_ips helper
# ---------------------------------------------------------------------------

def test_unique_ips_filters_loopback():
    ports = [_entry("127.0.0.1:22"), _entry("192.168.1.1:80")]
    ips = _unique_ips(ports)
    assert "127.0.0.1" not in ips
    assert "192.168.1.1" in ips


def test_unique_ips_deduplicates():
    ports = [_entry("10.0.0.1:22"), _entry("10.0.0.1:80")]
    ips = _unique_ips(ports)
    assert ips.count("10.0.0.1") == 1


def test_unique_ips_filters_wildcard():
    ports = [_entry("0.0.0.0:80"), _entry(":::443")]
    ips = _unique_ips(ports)
    assert ips == []


# ---------------------------------------------------------------------------
# cmd_geo
# ---------------------------------------------------------------------------

def test_returns_zero_on_success():
    with patch("portwatch.commands.geo_cmd.scan_ports", return_value=[_entry("10.1.2.3:443")]):
        with patch("portwatch.commands.geo_cmd.enrich_with_geoip", return_value=MagicMock(__str__=lambda s: "10.1.2.3")):
            rc = cmd_geo(_args())
    assert rc == 0


def test_no_routable_ips_prints_message(capsys):
    with patch("portwatch.commands.geo_cmd.scan_ports", return_value=[_entry("0.0.0.0:80")]):
        rc = cmd_geo(_args())
    assert rc == 0
    captured = capsys.readouterr()
    assert "No routable" in captured.out


def test_resolve_flag_calls_resolve_hostname(capsys):
    with patch("portwatch.commands.geo_cmd.scan_ports", return_value=[_entry("10.9.8.7:22")]):
        with patch("portwatch.commands.geo_cmd.enrich_with_geoip", return_value=MagicMock(__str__=lambda s: "10.9.8.7")):
            with patch("portwatch.commands.geo_cmd.resolve_hostname", return_value="myhost.local") as mock_resolve:
                rc = cmd_geo(_args(resolve=True))
    mock_resolve.assert_called_once_with("10.9.8.7")
    assert rc == 0


# ---------------------------------------------------------------------------
# register_subcommands
# ---------------------------------------------------------------------------

def test_register_adds_geo_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    args = parser.parse_args(["geo"])
    assert hasattr(args, "func")
