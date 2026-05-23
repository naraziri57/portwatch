"""Network topology snapshot — groups open ports by host/interface address."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List

from portwatch.scanner import PortEntry


@dataclass
class HostNode:
    """All ports bound to a single address."""

    address: str
    ports: List[PortEntry] = field(default_factory=list)

    def add(self, entry: PortEntry) -> None:
        if entry not in self.ports:
            self.ports.append(entry)

    def port_numbers(self) -> List[int]:
        return sorted({e.port for e in self.ports})

    def protocols(self) -> List[str]:
        return sorted({e.proto for e in self.ports})

    def summary(self) -> str:
        nums = ", ".join(str(p) for p in self.port_numbers())
        return f"{self.address}: [{nums}]"

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "ports": [str(e) for e in self.ports],
            "port_numbers": self.port_numbers(),
            "protocols": self.protocols(),
        }


@dataclass
class TopologyMap:
    """Full topology: mapping from address -> HostNode."""

    nodes: Dict[str, HostNode] = field(default_factory=dict)

    def add_entry(self, entry: PortEntry) -> None:
        addr = entry.address or "0.0.0.0"
        if addr not in self.nodes:
            self.nodes[addr] = HostNode(address=addr)
        self.nodes[addr].add(entry)

    def all_addresses(self) -> List[str]:
        return sorted(self.nodes.keys())

    def is_empty(self) -> bool:
        return len(self.nodes) == 0

    def to_dict(self) -> dict:
        return {addr: node.to_dict() for addr, node in sorted(self.nodes.items())}


def build_topology(ports: List[PortEntry]) -> TopologyMap:
    """Build a TopologyMap from a flat list of PortEntry objects."""
    topo = TopologyMap()
    for entry in ports:
        topo.add_entry(entry)
    return topo
