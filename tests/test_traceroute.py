"""Unit tests for portwatch.traceroute."""
from __future__ import annotations

import pytest

from portwatch.scanner import PortEntry
from portwatch.traceroute import (
    HopResult,
    TracerouteResult,
    run_traceroute,
)


def _entry(port: int = 8080, proto: str = "tcp", address: str = "127.0.0.1") -> PortEntry:
    return PortEntry(port=port, proto=proto, address=address, process=None)


# ---------------------------------------------------------------------------
# HopResult
# ---------------------------------------------------------------------------

class TestHopResult:
    def test_str_normal(self):
        h = HopResult(ttl=1, address="10.0.0.1", rtt_ms=3.5)
        assert "10.0.0.1" in str(h)
        assert "3.5 ms" in str(h)

    def test_str_timeout(self):
        h = HopResult(ttl=2, address=None, rtt_ms=None, timed_out=True)
        assert "* * *" in str(h)

    def test_to_dict_keys(self):
        h = HopResult(ttl=1, address="1.2.3.4", rtt_ms=10.0)
        d = h.to_dict()
        assert set(d.keys()) == {"ttl", "address", "rtt_ms", "timed_out"}

    def test_to_dict_rounds_rtt(self):
        h = HopResult(ttl=1, address="1.2.3.4", rtt_ms=1.23456789)
        assert h.to_dict()["rtt_ms"] == 1.235

    def test_to_dict_none_rtt(self):
        h = HopResult(ttl=1, address=None, rtt_ms=None, timed_out=True)
        assert h.to_dict()["rtt_ms"] is None


# ---------------------------------------------------------------------------
# TracerouteResult
# ---------------------------------------------------------------------------

class TestTracerouteResult:
    def test_to_dict_contains_port(self):
        r = TracerouteResult(entry=_entry(port=443))
        assert r.to_dict()["port"] == 443

    def test_to_dict_hops_list(self):
        r = TracerouteResult(entry=_entry())
        r.hops.append(HopResult(ttl=1, address="10.0.0.1", rtt_ms=2.0))
        assert len(r.to_dict()["hops"]) == 1

    def test_summary_contains_destination(self):
        r = TracerouteResult(entry=_entry(port=80))
        assert "80" in r.summary()

    def test_summary_reached_message(self):
        r = TracerouteResult(entry=_entry(), reached=True)
        assert "reached" in r.summary()

    def test_summary_not_reached_message(self):
        r = TracerouteResult(entry=_entry(), reached=False)
        assert "not reached" in r.summary()


# ---------------------------------------------------------------------------
# run_traceroute validation
# ---------------------------------------------------------------------------

def test_invalid_max_hops_zero_raises():
    with pytest.raises(ValueError, match="max_hops"):
        run_traceroute(_entry(), max_hops=0)


def test_invalid_max_hops_too_large_raises():
    with pytest.raises(ValueError, match="max_hops"):
        run_traceroute(_entry(), max_hops=65)


def test_invalid_timeout_raises():
    with pytest.raises(ValueError, match="timeout"):
        run_traceroute(_entry(), timeout=0.0)


def test_run_traceroute_returns_result(monkeypatch):
    """Patch _probe_hop so no real network calls happen."""
    from portwatch import traceroute as tr

    def _fake_probe(host, port, ttl, timeout):
        return HopResult(ttl=ttl, address=host, rtt_ms=1.0)

    monkeypatch.setattr(tr, "_probe_hop", _fake_probe)
    result = run_traceroute(_entry(), max_hops=3)
    assert isinstance(result, TracerouteResult)
    assert result.reached is True
    assert len(result.hops) == 1  # stops on first non-timeout


def test_run_traceroute_all_timeouts(monkeypatch):
    from portwatch import traceroute as tr

    def _fake_timeout(host, port, ttl, timeout):
        return HopResult(ttl=ttl, address=None, rtt_ms=None, timed_out=True)

    monkeypatch.setattr(tr, "_probe_hop", _fake_timeout)
    result = run_traceroute(_entry(), max_hops=3)
    assert result.reached is False
    assert len(result.hops) == 3
