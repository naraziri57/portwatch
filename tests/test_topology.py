"""Tests for portwatch.topology."""
from __future__ import annotations

import pytest

from portwatch.scanner import PortEntry
from portwatch.topology import HostNode, TopologyMap, build_topology


def _e(port: int, proto: str = "tcp", address: str = "0.0.0.0", process: str | None = None) -> PortEntry:
    return PortEntry(port=port, proto=proto, address=address, process=process)


# ---------------------------------------------------------------------------
# HostNode
# ---------------------------------------------------------------------------

class TestHostNode:
    def test_add_increases_ports(self):
        node = HostNode(address="127.0.0.1")
        node.add(_e(80, address="127.0.0.1"))
        assert len(node.ports) == 1

    def test_add_deduplicates(self):
        node = HostNode(address="127.0.0.1")
        entry = _e(80, address="127.0.0.1")
        node.add(entry)
        node.add(entry)
        assert len(node.ports) == 1

    def test_port_numbers_sorted(self):
        node = HostNode(address="0.0.0.0")
        node.add(_e(443))
        node.add(_e(80))
        assert node.port_numbers() == [80, 443]

    def test_protocols_unique(self):
        node = HostNode(address="0.0.0.0")
        node.add(_e(80, proto="tcp"))
        node.add(_e(53, proto="udp"))
        node.add(_e(8080, proto="tcp"))
        assert node.protocols() == ["tcp", "udp"]

    def test_summary_format(self):
        node = HostNode(address="10.0.0.1")
        node.add(_e(22, address="10.0.0.1"))
        node.add(_e(80, address="10.0.0.1"))
        s = node.summary()
        assert "10.0.0.1" in s
        assert "22" in s
        assert "80" in s

    def test_to_dict_keys(self):
        node = HostNode(address="::1")
        node.add(_e(443, address="::1"))
        d = node.to_dict()
        assert set(d.keys()) == {"address", "ports", "port_numbers", "protocols"}


# ---------------------------------------------------------------------------
# TopologyMap
# ---------------------------------------------------------------------------

class TestTopologyMap:
    def test_empty_by_default(self):
        topo = TopologyMap()
        assert topo.is_empty()

    def test_add_entry_creates_node(self):
        topo = TopologyMap()
        topo.add_entry(_e(80, address="192.168.1.1"))
        assert "192.168.1.1" in topo.nodes

    def test_missing_address_defaults(self):
        entry = PortEntry(port=80, proto="tcp", address=None, process=None)
        topo = TopologyMap()
        topo.add_entry(entry)
        assert "0.0.0.0" in topo.nodes

    def test_all_addresses_sorted(self):
        topo = TopologyMap()
        topo.add_entry(_e(80, address="10.0.0.2"))
        topo.add_entry(_e(22, address="10.0.0.1"))
        assert topo.all_addresses() == ["10.0.0.1", "10.0.0.2"]

    def test_to_dict_contains_addresses(self):
        topo = TopologyMap()
        topo.add_entry(_e(443, address="1.2.3.4"))
        d = topo.to_dict()
        assert "1.2.3.4" in d


# ---------------------------------------------------------------------------
# build_topology
# ---------------------------------------------------------------------------

def test_build_topology_groups_by_address():
    ports = [
        _e(80, address="10.0.0.1"),
        _e(443, address="10.0.0.1"),
        _e(22, address="10.0.0.2"),
    ]
    topo = build_topology(ports)
    assert len(topo.nodes) == 2
    assert topo.nodes["10.0.0.1"].port_numbers() == [80, 443]
    assert topo.nodes["10.0.0.2"].port_numbers() == [22]


def test_build_topology_empty_list():
    topo = build_topology([])
    assert topo.is_empty()
