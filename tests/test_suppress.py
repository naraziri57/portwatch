"""Tests for portwatch.suppress."""

import json
import pytest
from pathlib import Path

from portwatch.scanner import PortEntry
from portwatch.suppress import (
    SuppressRule,
    SuppressList,
    load_suppress_list,
    save_suppress_list,
)


def _entry(port=8080, proto="tcp", process="nginx"):
    return PortEntry(port=port, proto=proto, process=process)


class TestSuppressRule:
    def test_match_by_port(self):
        rule = SuppressRule(port=8080)
        assert rule.matches(_entry(port=8080))
        assert not rule.matches(_entry(port=9090))

    def test_match_by_proto(self):
        rule = SuppressRule(proto="udp")
        assert rule.matches(_entry(proto="udp"))
        assert not rule.matches(_entry(proto="tcp"))

    def test_match_by_process(self):
        rule = SuppressRule(process="nginx")
        assert rule.matches(_entry(process="nginx"))
        assert not rule.matches(_entry(process="sshd"))

    def test_match_combined(self):
        rule = SuppressRule(port=8080, proto="tcp")
        assert rule.matches(_entry(port=8080, proto="tcp"))
        assert not rule.matches(_entry(port=8080, proto="udp"))

    def test_empty_rule_matches_all(self):
        rule = SuppressRule()
        assert rule.matches(_entry())

    def test_to_dict_excludes_none(self):
        rule = SuppressRule(port=22)
        d = rule.to_dict()
        assert "port" in d
        assert "proto" not in d
        assert "process" not in d

    def test_roundtrip(self):
        rule = SuppressRule(port=443, proto="tcp", process="nginx")
        assert SuppressRule.from_dict(rule.to_dict()) == rule


class TestSuppressList:
    def test_is_suppressed_true(self):
        sl = SuppressList(rules=[SuppressRule(port=8080)])
        assert sl.is_suppressed(_entry(port=8080))

    def test_is_suppressed_false(self):
        sl = SuppressList(rules=[SuppressRule(port=8080)])
        assert not sl.is_suppressed(_entry(port=9090))

    def test_filter_entries_removes_suppressed(self):
        sl = SuppressList(rules=[SuppressRule(port=8080)])
        entries = [_entry(port=8080), _entry(port=443)]
        result = sl.filter_entries(entries)
        assert len(result) == 1
        assert result[0].port == 443

    def test_add_rule(self):
        sl = SuppressList()
        sl.add(SuppressRule(port=22))
        assert len(sl.rules) == 1

    def test_roundtrip(self):
        sl = SuppressList(rules=[SuppressRule(port=22, proto="tcp")])
        sl2 = SuppressList.from_dict(sl.to_dict())
        assert len(sl2.rules) == 1
        assert sl2.rules[0].port == 22


def test_load_missing_file_returns_empty(tmp_path):
    sl = load_suppress_list(tmp_path / "nope.json")
    assert sl.rules == []


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "suppress.json"
    sl = SuppressList(rules=[SuppressRule(port=80, proto="tcp")])
    save_suppress_list(path, sl)
    loaded = load_suppress_list(path)
    assert len(loaded.rules) == 1
    assert loaded.rules[0].port == 80


def test_save_creates_valid_json(tmp_path):
    path = tmp_path / "suppress.json"
    sl = SuppressList(rules=[SuppressRule(process="sshd")])
    save_suppress_list(path, sl)
    data = json.loads(path.read_text())
    assert "rules" in data
