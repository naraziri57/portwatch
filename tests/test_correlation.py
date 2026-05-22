"""Tests for portwatch.correlation."""

from __future__ import annotations

import pytest

from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent
from portwatch.correlation import CorrelatedGroup, correlate_events


def _entry(port: int, proto: str = "tcp", process: str | None = "svc") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


def _ev(kind: str, port: int, proto: str = "tcp", process: str | None = "svc") -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port, proto, process))


# ---------------------------------------------------------------------------
# CorrelatedGroup.summary
# ---------------------------------------------------------------------------

class TestCorrelatedGroupSummary:
    def test_summary_contains_pattern(self):
        g = CorrelatedGroup(pattern="restart", events=[_ev("OPENED", 8080)])
        assert "restart" in g.summary()

    def test_summary_contains_port(self):
        g = CorrelatedGroup(pattern="restart", events=[_ev("OPENED", 9090)])
        assert "9090" in g.summary()

    def test_summary_contains_event_count(self):
        g = CorrelatedGroup(pattern="restart", events=[_ev("OPENED", 80), _ev("CLOSED", 80)])
        assert "2" in g.summary()


# ---------------------------------------------------------------------------
# correlate_events — restart
# ---------------------------------------------------------------------------

class TestRestartPattern:
    def test_detects_restart(self):
        events = [_ev("OPENED", 8080), _ev("CLOSED", 8080)]
        groups = correlate_events(events)
        patterns = [g.pattern for g in groups]
        assert "restart" in patterns

    def test_restart_group_has_two_events(self):
        events = [_ev("OPENED", 8080), _ev("CLOSED", 8080)]
        groups = correlate_events(events)
        restart = next(g for g in groups if g.pattern == "restart")
        assert len(restart.events) == 2

    def test_no_restart_without_matching_process(self):
        events = [
            _ev("OPENED", 8080, process="nginx"),
            _ev("CLOSED", 8080, process="apache"),
        ]
        groups = correlate_events(events)
        patterns = [g.pattern for g in groups]
        assert "restart" not in patterns


# ---------------------------------------------------------------------------
# correlate_events — port-swap
# ---------------------------------------------------------------------------

class TestPortSwapPattern:
    def test_detects_port_swap(self):
        events = [
            _ev("OPENED", 9000, process="app"),
            _ev("CLOSED", 8000, process="app"),
        ]
        groups = correlate_events(events)
        patterns = [g.pattern for g in groups]
        assert "port-swap" in patterns

    def test_no_port_swap_different_processes(self):
        events = [
            _ev("OPENED", 9000, process="app1"),
            _ev("CLOSED", 8000, process="app2"),
        ]
        groups = correlate_events(events)
        patterns = [g.pattern for g in groups]
        assert "port-swap" not in patterns


# ---------------------------------------------------------------------------
# correlate_events — process-change
# ---------------------------------------------------------------------------

class TestProcessChangePattern:
    def test_detects_process_change(self):
        events = [
            _ev("OPENED", 80, process="nginx"),
            _ev("CLOSED", 80, process="apache"),
        ]
        groups = correlate_events(events)
        patterns = [g.pattern for g in groups]
        assert "process-change" in patterns


# ---------------------------------------------------------------------------
# correlate_events — unclassified / edge cases
# ---------------------------------------------------------------------------

class TestUnclassified:
    def test_single_open_is_unclassified(self):
        events = [_ev("OPENED", 443)]
        groups = correlate_events(events)
        assert groups[0].pattern == "unclassified"

    def test_empty_input_returns_empty(self):
        assert correlate_events([]) == []

    def test_no_event_used_twice(self):
        events = [_ev("OPENED", 8080), _ev("CLOSED", 8080)]
        groups = correlate_events(events)
        all_events = [e for g in groups for e in g.events]
        assert len(all_events) == len(events)
