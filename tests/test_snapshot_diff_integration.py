"""Integration tests: snapshot_diff wired with real severity rules."""

import pytest

from portwatch.scanner import PortEntry
from portwatch.severity import Level, SeverityRule
from portwatch.snapshot_diff import compute_diff, SnapshotDiff


def _e(port: int, proto: str = "tcp", process: str | None = None) -> PortEntry:
    return PortEntry(port=port, proto=proto, local_address="0.0.0.0", process=process)


class TestSnapshotDiffIntegration:
    def test_full_lifecycle_open_then_close(self):
        empty: frozenset = frozenset()
        step1 = frozenset([_e(22), _e(80)])
        step2 = frozenset([_e(80)])

        diff1 = compute_diff(empty, step1)
        assert len(diff1.opened) == 2
        assert diff1.closed == []

        diff2 = compute_diff(step1, step2)
        assert diff2.opened == []
        assert len(diff2.closed) == 1
        assert diff2.closed[0].entry.port == 22

    def test_severity_escalates_known_port(self):
        rules = [
            SeverityRule(port=22, level=Level.CRITICAL),
            SeverityRule(port=80, level=Level.WARN),
        ]
        before: frozenset = frozenset()
        after = frozenset([_e(22), _e(80), _e(9090)])
        diff = compute_diff(before, after, severity_rules=rules)

        levels = {d.entry.port: d.level for d in diff.opened}
        assert levels[22] == Level.CRITICAL
        assert levels[80] == Level.WARN
        assert levels[9090] == Level.INFO

    def test_no_false_positives_on_identical_snapshots(self):
        ports = frozenset([_e(p) for p in range(1000, 1010)])
        diff = compute_diff(ports, ports)
        assert diff.is_empty

    def test_summary_contains_port_numbers(self):
        before: frozenset = frozenset()
        after = frozenset([_e(8443)])
        diff = compute_diff(before, after)
        assert "8443" in diff.summary()
