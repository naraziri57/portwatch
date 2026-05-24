"""Integration tests for the traceroute feature."""
from __future__ import annotations

from unittest.mock import patch

from portwatch.scanner import PortEntry
from portwatch.traceroute import HopResult, run_traceroute


def _entry(port: int = 8080, address: str = "127.0.0.1") -> PortEntry:
    return PortEntry(port=port, proto="tcp", address=address, process="test")


class TestTracerouteLifecycle:
    def test_single_hop_reached(self, monkeypatch):
        from portwatch import traceroute as tr

        def _fast(host, port, ttl, timeout):
            return HopResult(ttl=ttl, address=host, rtt_ms=0.8)

        monkeypatch.setattr(tr, "_probe_hop", _fast)
        result = run_traceroute(_entry(), max_hops=5)
        assert result.reached
        assert result.hops[0].ttl == 1
        assert result.hops[0].rtt_ms == 0.8

    def test_to_dict_roundtrip(self, monkeypatch):
        from portwatch import traceroute as tr

        monkeypatch.setattr(
            tr,
            "_probe_hop",
            lambda h, p, ttl, t: HopResult(ttl=ttl, address=h, rtt_ms=1.5),
        )
        result = run_traceroute(_entry(port=443), max_hops=2)
        d = result.to_dict()
        assert d["port"] == 443
        assert d["reached"] is True
        assert isinstance(d["hops"], list)
        assert d["hops"][0]["rtt_ms"] == 1.5

    def test_wildcard_address_uses_loopback(self, monkeypatch):
        from portwatch import traceroute as tr

        probed_hosts = []

        def _capture(host, port, ttl, timeout):
            probed_hosts.append(host)
            return HopResult(ttl=ttl, address=host, rtt_ms=1.0)

        monkeypatch.setattr(tr, "_probe_hop", _capture)
        e = PortEntry(port=80, proto="tcp", address="0.0.0.0", process=None)
        run_traceroute(e, max_hops=1)
        assert probed_hosts[0] == "127.0.0.1"

    def test_summary_includes_all_hops(self, monkeypatch):
        from portwatch import traceroute as tr

        hop_count = 0

        def _timeout(host, port, ttl, timeout):
            nonlocal hop_count
            hop_count += 1
            return HopResult(ttl=ttl, address=None, rtt_ms=None, timed_out=True)

        monkeypatch.setattr(tr, "_probe_hop", _timeout)
        result = run_traceroute(_entry(), max_hops=4)
        summary = result.summary()
        assert "4 hop" in summary
        assert "not reached" in summary
