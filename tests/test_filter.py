"""Tests for portwatch.filter."""

import json
import pytest
from pathlib import Path

from portwatch.scanner import PortEntry
from portwatch.filter import FilterRule, FilterSet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(port=80, proto="tcp", process="nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, process=process)


# ---------------------------------------------------------------------------
# FilterRule
# ---------------------------------------------------------------------------

class TestFilterRule:
    def test_match_by_port(self):
        rule = FilterRule(port=80)
        assert rule.matches(_entry(port=80))
        assert not rule.matches(_entry(port=443))

    def test_match_by_proto(self):
        rule = FilterRule(proto="udp")
        assert rule.matches(_entry(proto="udp"))
        assert not rule.matches(_entry(proto="tcp"))

    def test_match_by_process_exact(self):
        rule = FilterRule(process="nginx")
        assert rule.matches(_entry(process="nginx"))
        assert not rule.matches(_entry(process="apache"))

    def test_match_by_process_glob(self):
        rule = FilterRule(process="*python*")
        assert rule.matches(_entry(process="python3"))
        assert not rule.matches(_entry(process="nginx"))

    def test_match_all_fields(self):
        rule = FilterRule(port=443, proto="tcp", process="nginx")
        assert rule.matches(_entry(port=443, proto="tcp", process="nginx"))
        assert not rule.matches(_entry(port=80, proto="tcp", process="nginx"))

    def test_no_process_on_entry(self):
        rule = FilterRule(process="nginx")
        entry = PortEntry(port=80, proto="tcp", process=None)
        assert not rule.matches(entry)

    def test_proto_case_insensitive(self):
        rule = FilterRule(proto="TCP")
        assert rule.matches(_entry(proto="tcp"))

    def test_to_dict_skips_none(self):
        rule = FilterRule(port=22)
        d = rule.to_dict()
        assert d == {"port": 22}
        assert "proto" not in d

    def test_roundtrip_dict(self):
        rule = FilterRule(port=22, proto="tcp", process="sshd")
        assert FilterRule.from_dict(rule.to_dict()) == rule


# ---------------------------------------------------------------------------
# FilterSet
# ---------------------------------------------------------------------------

class TestFilterSet:
    def test_should_ignore_matching(self):
        fs = FilterSet(rules=[FilterRule(port=22)])
        assert fs.should_ignore(_entry(port=22))

    def test_should_not_ignore_non_matching(self):
        fs = FilterSet(rules=[FilterRule(port=22)])
        assert not fs.should_ignore(_entry(port=80))

    def test_apply_filters_entries(self):
        fs = FilterSet(rules=[FilterRule(port=22)])
        entries = [_entry(port=22), _entry(port=80), _entry(port=443)]
        result = fs.apply(entries)
        assert len(result) == 2
        assert all(e.port != 22 for e in result)

    def test_empty_filterset_passes_all(self):
        fs = FilterSet.empty()
        entries = [_entry(port=p) for p in (22, 80, 443)]
        assert fs.apply(entries) == entries

    def test_save_and_load(self, tmp_path: Path):
        p = tmp_path / "rules.json"
        fs = FilterSet(rules=[FilterRule(port=22, proto="tcp"), FilterRule(process="*test*")])
        fs.save(p)
        loaded = FilterSet.load(p)
        assert len(loaded.rules) == 2
        assert loaded.rules[0].port == 22
        assert loaded.rules[1].process == "*test*"

    def test_save_valid_json(self, tmp_path: Path):
        p = tmp_path / "rules.json"
        FilterSet(rules=[FilterRule(port=80)]).save(p)
        data = json.loads(p.read_text())
        assert isinstance(data, list)
        assert data[0]["port"] == 80
