"""Tests for portwatch.dependency."""
import pytest

from portwatch.dependency import (
    DependencyGroup,
    build_dependency_groups,
    find_related,
)
from portwatch.scanner import PortEntry


def _entry(port: int, proto: str = "tcp", process: str | None = None) -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


# ---------------------------------------------------------------------------
# DependencyGroup validation
# ---------------------------------------------------------------------------

class TestDependencyGroupValidation:
    def test_empty_members_raises(self):
        with pytest.raises(ValueError, match="at least one member"):
            DependencyGroup(members=frozenset())

    def test_single_member_ok(self):
        g = DependencyGroup(members=frozenset({80}))
        assert 80 in g.members


class TestDependencyGroupOverlaps:
    def test_overlapping_groups(self):
        a = DependencyGroup(members=frozenset({80, 443}))
        b = DependencyGroup(members=frozenset({443, 8080}))
        assert a.overlaps(b)

    def test_non_overlapping_groups(self):
        a = DependencyGroup(members=frozenset({80}))
        b = DependencyGroup(members=frozenset({22}))
        assert not a.overlaps(b)


class TestDependencyGroupSerialization:
    def test_to_dict_contains_members(self):
        g = DependencyGroup(members=frozenset({80, 443}), proto="tcp")
        d = g.to_dict()
        assert sorted(d["members"]) == [80, 443]
        assert d["proto"] == "tcp"

    def test_roundtrip(self):
        g = DependencyGroup(members=frozenset({22, 2222}), proto="tcp")
        assert DependencyGroup.from_dict(g.to_dict()) == g

    def test_summary_contains_ports(self):
        g = DependencyGroup(members=frozenset({80, 443}), proto="tcp")
        s = g.summary()
        assert "80" in s
        assert "443" in s
        assert "tcp" in s


# ---------------------------------------------------------------------------
# build_dependency_groups
# ---------------------------------------------------------------------------

class TestBuildDependencyGroups:
    def test_single_port_process_excluded(self):
        ports = [_entry(80, process="nginx")]
        groups = build_dependency_groups(ports)
        assert groups == []

    def test_two_ports_same_process_grouped(self):
        ports = [
            _entry(80, process="nginx"),
            _entry(443, process="nginx"),
        ]
        groups = build_dependency_groups(ports)
        assert len(groups) == 1
        assert frozenset({80, 443}) == groups[0].members

    def test_different_processes_separate_groups(self):
        ports = [
            _entry(80, process="nginx"),
            _entry(443, process="nginx"),
            _entry(5432, process="postgres"),
            _entry(5433, process="postgres"),
        ]
        groups = build_dependency_groups(ports)
        assert len(groups) == 2

    def test_no_process_grouped_under_unknown(self):
        ports = [_entry(1234), _entry(5678)]
        groups = build_dependency_groups(ports)
        assert len(groups) == 1


# ---------------------------------------------------------------------------
# find_related
# ---------------------------------------------------------------------------

def test_find_related_returns_matching_groups():
    g1 = DependencyGroup(members=frozenset({80, 443}))
    g2 = DependencyGroup(members=frozenset({22, 2222}))
    result = find_related(443, [g1, g2])
    assert result == [g1]


def test_find_related_returns_empty_when_no_match():
    g = DependencyGroup(members=frozenset({80}))
    assert find_related(9999, [g]) == []
