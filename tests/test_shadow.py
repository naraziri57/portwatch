"""Tests for portwatch.shadow shadow-port detection."""

from __future__ import annotations

import pytest

from portwatch.scanner import PortEntry
from portwatch.shadow import ShadowPort, detect_shadow_ports, _is_shadow_address


def _entry(port: int = 8080, proto: str = "tcp", address: str = "127.0.0.1",
           process: str | None = "sshd") -> PortEntry:
    return PortEntry(port=port, proto=proto, address=address, process=process)


class TestIsShadowAddress:
    def test_loopback_ipv4(self):
        assert _is_shadow_address("127.0.0.1") is True

    def test_loopback_ipv4_other(self):
        assert _is_shadow_address("127.1.2.3") is True

    def test_loopback_ipv6(self):
        assert _is_shadow_address("::1") is True

    def test_link_local_ipv4(self):
        assert _is_shadow_address("169.254.1.1") is True

    def test_link_local_ipv6(self):
        assert _is_shadow_address("fe80::1") is True

    def test_wildcard_ipv4_not_shadow(self):
        assert _is_shadow_address("0.0.0.0") is False

    def test_wildcard_ipv6_not_shadow(self):
        assert _is_shadow_address("::") is False

    def test_star_not_shadow(self):
        assert _is_shadow_address("*") is False

    def test_public_ip_not_shadow(self):
        assert _is_shadow_address("192.168.1.1") is False

    def test_invalid_string_not_shadow(self):
        assert _is_shadow_address("not-an-ip") is False


class TestDetectShadowPorts:
    def test_loopback_entry_detected(self):
        ports = [_entry(address="127.0.0.1")]
        result = detect_shadow_ports(ports)
        assert len(result) == 1
        assert result[0].reason == "loopback-only binding"

    def test_link_local_entry_detected(self):
        ports = [_entry(address="169.254.0.5")]
        result = detect_shadow_ports(ports)
        assert len(result) == 1
        assert result[0].reason == "link-local binding"

    def test_wildcard_not_detected(self):
        ports = [_entry(address="0.0.0.0")]
        assert detect_shadow_ports(ports) == []

    def test_public_not_detected(self):
        ports = [_entry(address="10.0.0.1")]
        assert detect_shadow_ports(ports) == []

    def test_mixed_list(self):
        ports = [
            _entry(port=22, address="0.0.0.0"),
            _entry(port=9000, address="127.0.0.1"),
            _entry(port=9001, address="fe80::1"),
        ]
        result = detect_shadow_ports(ports)
        assert len(result) == 2
        ports_found = {r.entry.port for r in result}
        assert ports_found == {9000, 9001}

    def test_str_representation(self):
        entry = _entry(port=3306, address="127.0.0.1", process="mysqld")
        shadow = ShadowPort(entry=entry, reason="loopback-only binding")
        s = str(shadow)
        assert "3306" in s
        assert "mysqld" in s
        assert "loopback" in s

    def test_str_unknown_process(self):
        entry = _entry(port=5432, address="127.0.0.1", process=None)
        shadow = ShadowPort(entry=entry, reason="loopback-only binding")
        assert "unknown" in str(shadow)
