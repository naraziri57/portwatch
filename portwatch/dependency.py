"""Track port dependency relationships — which ports commonly appear together."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Set

from portwatch.scanner import PortEntry


@dataclass
class DependencyGroup:
    """A set of ports that were observed open at the same time."""

    members: FrozenSet[int] = field(default_factory=frozenset)
    proto: str = "tcp"

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError("DependencyGroup must have at least one member port")

    def overlaps(self, other: "DependencyGroup") -> bool:
        """Return True if the two groups share at least one port."""
        return bool(self.members & other.members)

    def summary(self) -> str:
        ports = ", ".join(str(p) for p in sorted(self.members))
        return f"[{self.proto}] ports: {ports}"

    def to_dict(self) -> dict:
        return {"members": sorted(self.members), "proto": self.proto}

    @classmethod
    def from_dict(cls, data: dict) -> "DependencyGroup":
        return cls(
            members=frozenset(data["members"]),
            proto=data.get("proto", "tcp"),
        )


def build_dependency_groups(ports: List[PortEntry]) -> List[DependencyGroup]:
    """Group ports by process name — ports sharing a process are considered dependent."""
    process_map: dict[str, Set[int]] = {}
    proto_map: dict[str, str] = {}

    for entry in ports:
        key = entry.process or "<unknown>"
        process_map.setdefault(key, set()).add(entry.port)
        proto_map[key] = entry.proto

    groups: List[DependencyGroup] = []
    for proc, port_set in process_map.items():
        if len(port_set) >= 2:
            groups.append(
                DependencyGroup(
                    members=frozenset(port_set),
                    proto=proto_map[proc],
                )
            )
    return groups


def find_related(port: int, groups: List[DependencyGroup]) -> List[DependencyGroup]:
    """Return all groups that contain the given port number."""
    return [g for g in groups if port in g.members]
