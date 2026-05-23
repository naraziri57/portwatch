"""Tests for portwatch.grouping."""

import pytest

from portwatch.scanner import PortEntry
from portwatch.grouping import ProcessGroup, group_by_process, top_processes


def _entry(port: int, proto: str = "tcp", process: str | None = None) -> PortEntry:
    return PortEntry(port=port, proto=proto, local_addr="0.0.0.0", process=process)


# ---------------------------------------------------------------------------
# ProcessGroup
# ---------------------------------------------------------------------------

class TestProcessGroup:
    def test_add_increases_ports(self):
        g = ProcessGroup(process="nginx")
        g.add(_entry(80))
        g.add(_entry(443))
        assert len(g.ports) == 2

    def test_port_numbers_sorted_unique(self):
        g = ProcessGroup(process="nginx")
        g.add(_entry(443))
        g.add(_entry(80))
        g.add(_entry(80))  # duplicate
        assert g.port_numbers == [80, 443]

    def test_protocols_sorted_unique(self):
        g = ProcessGroup(process="sshd")
        g.add(_entry(22, proto="tcp"))
        g.add(_entry(22, proto="udp"))
        g.add(_entry(22, proto="tcp"))
        assert g.protocols == ["tcp", "udp"]

    def test_summary_contains_process(self):
        g = ProcessGroup(process="sshd")
        g.add(_entry(22))
        assert "sshd" in g.summary()

    def test_summary_contains_port(self):
        g = ProcessGroup(process="sshd")
        g.add(_entry(22))
        assert "22" in g.summary()

    def test_to_dict_keys(self):
        g = ProcessGroup(process="nginx")
        g.add(_entry(80))
        d = g.to_dict()
        assert set(d.keys()) == {"process", "port_count", "ports", "protocols"}

    def test_to_dict_port_count(self):
        g = ProcessGroup(process="nginx")
        g.add(_entry(80))
        g.add(_entry(443))
        assert g.to_dict()["port_count"] == 2


# ---------------------------------------------------------------------------
# group_by_process
# ---------------------------------------------------------------------------

class TestGroupByProcess:
    def test_groups_by_process_name(self):
        entries = [_entry(80, process="nginx"), _entry(443, process="nginx"), _entry(22, process="sshd")]
        groups = group_by_process(entries)
        assert set(groups.keys()) == {"nginx", "sshd"}
        assert len(groups["nginx"].ports) == 2

    def test_none_process_grouped_as_unknown(self):
        entries = [_entry(9999, process=None)]
        groups = group_by_process(entries)
        assert "<unknown>" in groups

    def test_empty_input_returns_empty_dict(self):
        assert group_by_process([]) == {}


# ---------------------------------------------------------------------------
# top_processes
# ---------------------------------------------------------------------------

class TestTopProcesses:
    def _make_groups(self):
        entries = (
            [_entry(p, process="nginx") for p in [80, 443, 8080]] +
            [_entry(p, process="sshd") for p in [22]] +
            [_entry(p, process="postgres") for p in [5432, 5433]]
        )
        return group_by_process(entries)

    def test_returns_top_n(self):
        groups = self._make_groups()
        top = top_processes(groups, n=2)
        assert len(top) == 2

    def test_sorted_descending_by_port_count(self):
        groups = self._make_groups()
        top = top_processes(groups, n=3)
        counts = [len(g.ports) for g in top]
        assert counts == sorted(counts, reverse=True)

    def test_n_larger_than_groups_returns_all(self):
        groups = self._make_groups()
        top = top_processes(groups, n=100)
        assert len(top) == len(groups)

    def test_zero_n_raises(self):
        with pytest.raises(ValueError):
            top_processes({}, n=0)
