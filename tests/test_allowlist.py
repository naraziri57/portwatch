"""Tests for portwatch.allowlist."""

from __future__ import annotations

import pytest

from portwatch.allowlist import AllowRule, Allowlist
from portwatch.scanner import PortEntry


def _entry(port: int = 80, proto: str = "tcp", process: str = "nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, local_addr="0.0.0.0", process=process)


class TestAllowRule:
    def test_match_by_port(self):
        rule = AllowRule(port=80)
        assert rule.matches(_entry(port=80))

    def test_no_match_wrong_port(self):
        rule = AllowRule(port=443)
        assert not rule.matches(_entry(port=80))

    def test_match_by_proto(self):
        rule = AllowRule(proto="tcp")
        assert rule.matches(_entry(proto="tcp"))

    def test_no_match_wrong_proto(self):
        rule = AllowRule(proto="udp")
        assert not rule.matches(_entry(proto="tcp"))

    def test_match_by_process_substring(self):
        rule = AllowRule(process="nginx")
        assert rule.matches(_entry(process="nginx: worker"))

    def test_no_match_wrong_process(self):
        rule = AllowRule(process="apache")
        assert not rule.matches(_entry(process="nginx"))

    def test_match_all_fields(self):
        rule = AllowRule(port=80, proto="tcp", process="nginx")
        assert rule.matches(_entry(port=80, proto="tcp", process="nginx"))

    def test_no_process_on_entry(self):
        entry = PortEntry(port=80, proto="tcp", local_addr="0.0.0.0", process=None)
        rule = AllowRule(process="nginx")
        assert not rule.matches(entry)

    def test_to_dict_excludes_none(self):
        rule = AllowRule(port=22)
        d = rule.to_dict()
        assert "port" in d
        assert "proto" not in d
        assert "process" not in d

    def test_roundtrip(self):
        rule = AllowRule(port=443, proto="tcp", process="sshd")
        assert AllowRule.from_dict(rule.to_dict()) == rule


class TestAllowlist:
    def test_empty_allowlist_allows_nothing(self):
        al = Allowlist()
        assert not al.is_allowed(_entry())

    def test_matching_rule_allows_entry(self):
        al = Allowlist(rules=[AllowRule(port=80)])
        assert al.is_allowed(_entry(port=80))

    def test_non_matching_rule_blocks_entry(self):
        al = Allowlist(rules=[AllowRule(port=443)])
        assert not al.is_allowed(_entry(port=80))

    def test_filter_allowed_removes_safe_entries(self):
        al = Allowlist(rules=[AllowRule(port=80)])
        entries = [_entry(port=80), _entry(port=443)]
        result = al.filter_allowed(entries)
        assert len(result) == 1
        assert result[0].port == 443

    def test_roundtrip_via_dict(self):
        al = Allowlist(rules=[AllowRule(port=22, proto="tcp")])
        restored = Allowlist.from_dict(al.to_dict())
        assert len(restored.rules) == 1
        assert restored.rules[0].port == 22

    def test_empty_from_dict(self):
        al = Allowlist.from_dict({})
        assert al.rules == []
