"""Group open ports by process name for summarized reporting."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from portwatch.scanner import PortEntry


@dataclass
class ProcessGroup:
    """All ports associated with a single process name."""

    process: str
    ports: List[PortEntry] = field(default_factory=list)

    def add(self, entry: PortEntry) -> None:
        self.ports.append(entry)

    @property
    def port_numbers(self) -> List[int]:
        return sorted({e.port for e in self.ports})

    @property
    def protocols(self) -> List[str]:
        return sorted({e.proto for e in self.ports})

    def summary(self) -> str:
        ports_str = ", ".join(str(p) for p in self.port_numbers)
        protos_str = "/".join(self.protocols)
        return f"{self.process} [{protos_str}] ports: {ports_str}"

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "port_count": len(self.ports),
            "ports": self.port_numbers,
            "protocols": self.protocols,
        }


def group_by_process(entries: List[PortEntry]) -> Dict[str, ProcessGroup]:
    """Return a mapping of process name -> ProcessGroup.

    Entries with no process name are grouped under the key '<unknown>'.
    """
    groups: Dict[str, ProcessGroup] = defaultdict(lambda: ProcessGroup(process="<unknown>"))
    for entry in entries:
        key = entry.process or "<unknown>"
        if key not in groups:
            groups[key] = ProcessGroup(process=key)
        groups[key].add(entry)
    return dict(groups)


def top_processes(groups: Dict[str, ProcessGroup], n: int = 5) -> List[ProcessGroup]:
    """Return the top-n groups sorted by number of open ports (descending)."""
    if n <= 0:
        raise ValueError("n must be a positive integer")
    return sorted(groups.values(), key=lambda g: len(g.ports), reverse=True)[:n]
