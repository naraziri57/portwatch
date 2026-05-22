"""Tests for portwatch.tags."""
import pytest
from portwatch.scanner import PortEntry
from portwatch.tags import TagRule, TagSet


def _entry(port=80, proto="tcp", process="nginx"):
    return PortEntry(port=port, proto=proto, local_addr="0.0.0.0", process=process)


class TestTagRule:
    def test_match_by_port(self):
        rule = TagRule(tag="web", port=80)
        assert rule.matches(_entry(port=80))

    def test_no_match_wrong_port(self):
        rule = TagRule(tag="web", port=443)
        assert not rule.matches(_entry(port=80))

    def test_match_by_proto(self):
        rule = TagRule(tag="udp-traffic", proto="udp")
        assert rule.matches(_entry(proto="udp"))

    def test_no_match_wrong_proto(self):
        rule = TagRule(tag="udp-traffic", proto="udp")
        assert not rule.matches(_entry(proto="tcp"))

    def test_match_by_process_substring(self):
        rule = TagRule(tag="nginx", process="ngi")
        assert rule.matches(_entry(process="nginx"))

    def test_no_match_process_none(self):
        rule = TagRule(tag="nginx", process="nginx")
        entry = PortEntry(port=80, proto="tcp", local_addr="0.0.0.0", process=None)
        assert not rule.matches(entry)

    def test_match_all_criteria(self):
        rule = TagRule(tag="secure-web", port=443, proto="tcp", process="nginx")
        assert rule.matches(_entry(port=443, proto="tcp", process="nginx"))

    def test_no_criteria_matches_anything(self):
        rule = TagRule(tag="all")
        assert rule.matches(_entry())

    def test_to_dict_roundtrip(self):
        rule = TagRule(tag="db", port=5432, proto="tcp", process="postgres")
        assert TagRule.from_dict(rule.to_dict()) == rule

    def test_to_dict_omits_none_fields(self):
        rule = TagRule(tag="x")
        d = rule.to_dict()
        assert "port" not in d
        assert "proto" not in d
        assert "process" not in d


class TestTagSet:
    def test_resolve_returns_matching_tags(self):
        ts = TagSet(rules=[
            TagRule(tag="web", port=80),
            TagRule(tag="nginx", process="nginx"),
        ])
        tags = ts.resolve(_entry(port=80, process="nginx"))
        assert tags == frozenset({"web", "nginx"})

    def test_resolve_empty_when_no_match(self):
        ts = TagSet(rules=[TagRule(tag="db", port=5432)])
        assert ts.resolve(_entry(port=80)) == frozenset()

    def test_resolve_empty_rules(self):
        ts = TagSet()
        assert ts.resolve(_entry()) == frozenset()

    def test_to_dict_roundtrip(self):
        ts = TagSet(rules=[
            TagRule(tag="web", port=80),
            TagRule(tag="udp", proto="udp"),
        ])
        restored = TagSet.from_dict(ts.to_dict())
        assert restored.rules == ts.rules

    def test_from_dict_empty(self):
        ts = TagSet.from_dict({})
        assert ts.rules == []
