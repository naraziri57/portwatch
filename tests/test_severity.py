"""Tests for portwatch.severity."""
import pytest

from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent
from portwatch.severity import Level, SeverityRule, classify


def _entry(port: int, proto: str = "tcp", process: str = "svc") -> PortEntry:
    return PortEntry(port=port, proto=proto, local_address="0.0.0.0", process=process)


def _ev(port: int, kind: str = "opened", proto: str = "tcp") -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port, proto))


# ---------------------------------------------------------------------------
# Level enum
# ---------------------------------------------------------------------------

def test_level_values_are_strings():
    assert Level.LOW.value == "low"
    assert Level.CRITICAL.value == "critical"


# ---------------------------------------------------------------------------
# SeverityRule
# ---------------------------------------------------------------------------

class TestSeverityRule:
    def test_matches_by_port(self):
        rule = SeverityRule(ports=[8080], level=Level.HIGH)
        assert rule.matches(_ev(8080))

    def test_no_match_wrong_port(self):
        rule = SeverityRule(ports=[8080], level=Level.HIGH)
        assert not rule.matches(_ev(9090))

    def test_empty_ports_never_matches(self):
        rule = SeverityRule(ports=[], level=Level.CRITICAL)
        assert not rule.matches(_ev(22))

    def test_roundtrip(self):
        rule = SeverityRule(ports=[443, 80], level=Level.MEDIUM)
        restored = SeverityRule.from_dict(rule.to_dict())
        assert restored.ports == rule.ports
        assert restored.level == rule.level


# ---------------------------------------------------------------------------
# classify — built-in heuristics
# ---------------------------------------------------------------------------

class TestClassify:
    def test_opened_sensitive_port_is_critical(self):
        assert classify(_ev(22, "opened")) == Level.CRITICAL

    def test_opened_privileged_port_is_high(self):
        assert classify(_ev(80, "opened")) == Level.HIGH

    def test_opened_unprivileged_port_is_medium(self):
        assert classify(_ev(8080, "opened")) == Level.MEDIUM

    def test_closed_sensitive_port_is_medium(self):
        assert classify(_ev(22, "closed")) == Level.MEDIUM

    def test_closed_normal_port_is_low(self):
        assert classify(_ev(8080, "closed")) == Level.LOW

    def test_custom_rule_overrides_heuristic(self):
        rule = SeverityRule(ports=[8080], level=Level.CRITICAL)
        assert classify(_ev(8080, "opened"), rules=[rule]) == Level.CRITICAL

    def test_first_matching_rule_wins(self):
        rules = [
            SeverityRule(ports=[9000], level=Level.LOW),
            SeverityRule(ports=[9000], level=Level.CRITICAL),
        ]
        assert classify(_ev(9000, "opened"), rules=rules) == Level.LOW

    def test_unmatched_rule_falls_through_to_heuristic(self):
        rule = SeverityRule(ports=[1234], level=Level.HIGH)
        # port 22 not in rule → heuristic applies
        assert classify(_ev(22, "opened"), rules=[rule]) == Level.CRITICAL
