"""Tests for portwatch.reachability."""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from portwatch.reachability import (
    ReachabilityResult,
    _resolve_address,
    check_reachability,
    unreachable_ports,
)
from portwatch.scanner import PortEntry


def _entry(port: int = 8080, proto: str = "tcp", address: str = "0.0.0.0", process: str = "app") -> PortEntry:
    return PortEntry(port=port, proto=proto, address=address, process=process)


class TestReachabilityResult:
    def test_str_reachable(self):
        r = ReachabilityResult(entry=_entry(), reachable=True)
        assert "reachable" in str(r)
        assert "8080" in str(r)

    def test_str_unreachable_with_error(self):
        r = ReachabilityResult(entry=_entry(), reachable=False, error="Connection refused")
        assert "unreachable" in str(r)
        assert "Connection refused" in str(r)

    def test_str_no_error_field_when_none(self):
        r = ReachabilityResult(entry=_entry(), reachable=True)
        assert "[" not in str(r)


class TestResolveAddress:
    @pytest.mark.parametrize("addr", ["", "0.0.0.0", "::", "*"])
    def test_wildcards_become_localhost(self, addr):
        assert _resolve_address(addr) == "127.0.0.1"

    def test_specific_address_unchanged(self):
        assert _resolve_address("192.168.1.1") == "192.168.1.1"

    def test_loopback_unchanged(self):
        assert _resolve_address("127.0.0.1") == "127.0.0.1"


class TestCheckReachability:
    def test_successful_probe_returns_reachable(self):
        entry = _entry(port=9000)
        with patch("portwatch.reachability._probe", return_value=None):
            results = check_reachability([entry])
        assert len(results) == 1
        assert results[0].reachable is True
        assert results[0].error is None

    def test_failed_probe_returns_unreachable(self):
        entry = _entry(port=9001)
        with patch("portwatch.reachability._probe", return_value="Connection refused"):
            results = check_reachability([entry])
        assert results[0].reachable is False
        assert results[0].error == "Connection refused"

    def test_udp_skipped_when_tcp_only(self):
        udp_entry = _entry(port=53, proto="udp")
        with patch("portwatch.reachability._probe") as mock_probe:
            results = check_reachability([udp_entry], tcp_only=True)
        mock_probe.assert_not_called()
        assert results == []

    def test_udp_included_when_not_tcp_only(self):
        udp_entry = _entry(port=53, proto="udp")
        with patch("portwatch.reachability._probe", return_value=None):
            results = check_reachability([udp_entry], tcp_only=False)
        assert len(results) == 1

    def test_empty_list_returns_empty(self):
        assert check_reachability([]) == []

    def test_multiple_entries_all_probed(self):
        entries = [_entry(port=p) for p in (80, 443, 8080)]
        with patch("portwatch.reachability._probe", return_value=None):
            results = check_reachability(entries)
        assert len(results) == 3


class TestUnreachablePorts:
    def test_filters_to_failed_only(self):
        e1 = _entry(port=80)
        e2 = _entry(port=443)
        results = [
            ReachabilityResult(entry=e1, reachable=True),
            ReachabilityResult(entry=e2, reachable=False, error="timeout"),
        ]
        bad = unreachable_ports(results)
        assert len(bad) == 1
        assert bad[0].entry.port == 443

    def test_all_reachable_returns_empty(self):
        results = [ReachabilityResult(entry=_entry(port=p), reachable=True) for p in (80, 443)]
        assert unreachable_ports(results) == []
