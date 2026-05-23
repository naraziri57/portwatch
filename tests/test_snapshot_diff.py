"""Tests for portwatch.snapshot_diff."""

import pytest

from portwatch.scanner import PortEntry
from portwatch.severity import Level, SeverityRule
from portwatch.snapshot_diff import PortDiff, SnapshotDiff, compute_diff


def _e(port: int, proto: str = "tcp", process: str | None = None) -> PortEntry:
    return PortEntry(port=port, proto=proto, local_address="0.0.0.0", process=process)


# ---------------------------------------------------------------------------
# PortDiff
# ---------------------------------------------------------------------------

class TestPortDiff:
    def test_str_opened(self):
        d = PortDiff(kind="opened", entry=_e(80), level=Level.INFO)
        assert "+" in str(d)
        assert "INFO" in str(d).upper()

    def test_str_closed(self):
        d = PortDiff(kind="closed", entry=_e(80), level=Level.WARN)
        assert "-" in str(d)

    def test_default_level_is_info(self):
        d = PortDiff(kind="opened", entry=_e(443))
        assert d.level == Level.INFO


# ---------------------------------------------------------------------------
# SnapshotDiff
# ---------------------------------------------------------------------------

class TestSnapshotDiff:
    def test_empty_when_no_changes(self):
        sd = SnapshotDiff()
        assert sd.is_empty

    def test_not_empty_with_opened(self):
        sd = SnapshotDiff(opened=[PortDiff(kind="opened", entry=_e(22))])
        assert not sd.is_empty

    def test_all_changes_combines_lists(self):
        sd = SnapshotDiff(
            opened=[PortDiff(kind="opened", entry=_e(22))],
            closed=[PortDiff(kind="closed", entry=_e(80))],
        )
        assert len(sd.all_changes) == 2

    def test_summary_empty(self):
        assert "No changes" in SnapshotDiff().summary()

    def test_summary_non_empty(self):
        sd = SnapshotDiff(opened=[PortDiff(kind="opened", entry=_e(8080))])
        s = sd.summary()
        assert "+" in s


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------

class TestComputeDiff:
    def test_no_change(self):
        ports = frozenset([_e(80), _e(443)])
        diff = compute_diff(ports, ports)
        assert diff.is_empty

    def test_detects_opened(self):
        before = frozenset([_e(80)])
        after = frozenset([_e(80), _e(443)])
        diff = compute_diff(before, after)
        assert len(diff.opened) == 1
        assert diff.opened[0].entry.port == 443

    def test_detects_closed(self):
        before = frozenset([_e(80), _e(22)])
        after = frozenset([_e(80)])
        diff = compute_diff(before, after)
        assert len(diff.closed) == 1
        assert diff.closed[0].entry.port == 22

    def test_opened_sorted_by_port(self):
        before: frozenset = frozenset()
        after = frozenset([_e(9000), _e(22), _e(443)])
        diff = compute_diff(before, after)
        ports = [d.entry.port for d in diff.opened]
        assert ports == sorted(ports)

    def test_severity_rule_applied(self):
        rule = SeverityRule(port=22, level=Level.CRITICAL)
        before: frozenset = frozenset()
        after = frozenset([_e(22)])
        diff = compute_diff(before, after, severity_rules=[rule])
        assert diff.opened[0].level == Level.CRITICAL

    def test_unmatched_rule_keeps_info(self):
        rule = SeverityRule(port=9999, level=Level.CRITICAL)
        before: frozenset = frozenset()
        after = frozenset([_e(80)])
        diff = compute_diff(before, after, severity_rules=[rule])
        assert diff.opened[0].level == Level.INFO
