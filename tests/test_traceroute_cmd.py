"""Tests for portwatch.commands.traceroute_cmd."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.traceroute_cmd import cmd_traceroute, register_subcommands
from portwatch.scanner import PortEntry
from portwatch.traceroute import HopResult, TracerouteResult


def _entry(port: int = 80, proto: str = "tcp") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="127.0.0.1", process=None)


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(max_hops=5, timeout=1.0, limit=5, fail_unreachable=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _reached_result(entry: PortEntry) -> TracerouteResult:
    r = TracerouteResult(entry=entry, reached=True)
    r.hops.append(HopResult(ttl=1, address="127.0.0.1", rtt_ms=0.5))
    return r


def test_returns_zero_on_success():
    entry = _entry()
    with patch("portwatch.commands.traceroute_cmd.scan_ports", return_value=[entry]), \
         patch("portwatch.commands.traceroute_cmd.run_traceroute", return_value=_reached_result(entry)):
        assert cmd_traceroute(_args()) == 0


def test_returns_one_on_scan_failure():
    with patch("portwatch.commands.traceroute_cmd.scan_ports", side_effect=RuntimeError("fail")):
        assert cmd_traceroute(_args()) == 1


def test_no_ports_returns_zero():
    with patch("portwatch.commands.traceroute_cmd.scan_ports", return_value=[]):
        assert cmd_traceroute(_args()) == 0


def test_no_tcp_ports_returns_zero():
    udp = PortEntry(port=53, proto="udp", address="0.0.0.0", process=None)
    with patch("portwatch.commands.traceroute_cmd.scan_ports", return_value=[udp]):
        assert cmd_traceroute(_args()) == 0


def test_limit_respected():
    entries = [_entry(port=p) for p in range(10)]
    results = [_reached_result(e) for e in entries]
    called = []

    def _fake_trace(entry, **kw):
        called.append(entry)
        return _reached_result(entry)

    with patch("portwatch.commands.traceroute_cmd.scan_ports", return_value=entries), \
         patch("portwatch.commands.traceroute_cmd.run_traceroute", side_effect=_fake_trace):
        cmd_traceroute(_args(limit=3))

    assert len(called) == 3


def test_fail_unreachable_returns_two():
    entry = _entry()
    unreached = TracerouteResult(entry=entry, reached=False)
    with patch("portwatch.commands.traceroute_cmd.scan_ports", return_value=[entry]), \
         patch("portwatch.commands.traceroute_cmd.run_traceroute", return_value=unreached):
        assert cmd_traceroute(_args(fail_unreachable=True)) == 2


def test_traceroute_exception_returns_one():
    entry = _entry()
    with patch("portwatch.commands.traceroute_cmd.scan_ports", return_value=[entry]), \
         patch("portwatch.commands.traceroute_cmd.run_traceroute", side_effect=OSError("boom")):
        assert cmd_traceroute(_args()) == 1


def test_register_subcommands_adds_parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    args = parser.parse_args(["traceroute", "--max-hops", "3"])
    assert args.max_hops == 3
