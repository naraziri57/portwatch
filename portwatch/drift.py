"""Drift detection: compare current ports against a saved reference profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Set

from portwatch.scanner import PortEntry


@dataclass(frozen=True)
class DriftResult:
    added: FrozenSet[PortEntry] = field(default_factory=frozenset)
    removed: FrozenSet[PortEntry] = field(default_factory=frozenset)

    @property
    def is_clean(self) -> bool:
        return not self.added and not self.removed

    def summary(self) -> str:
        if self.is_clean:
            return "No drift detected."
        parts: List[str] = []
        if self.added:
            ports = ", ".join(str(e.port) for e in sorted(self.added, key=lambda e: e.port))
            parts.append(f"+{len(self.added)} opened ({ports})")
        if self.removed:
            ports = ", ".join(str(e.port) for e in sorted(self.removed, key=lambda e: e.port))
            parts.append(f"-{len(self.removed)} closed ({ports})")
        return "Drift: " + ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "added": [e.port for e in sorted(self.added, key=lambda e: e.port)],
            "removed": [e.port for e in sorted(self.removed, key=lambda e: e.port)],
            "clean": self.is_clean,
        }


def detect_drift(
    reference: Set[PortEntry],
    current: Set[PortEntry],
) -> DriftResult:
    """Return a DriftResult describing what changed between reference and current."""
    ref_keys = {(e.port, e.proto) for e in reference}
    cur_keys = {(e.port, e.proto) for e in current}

    added = frozenset(e for e in current if (e.port, e.proto) not in ref_keys)
    removed = frozenset(e for e in reference if (e.port, e.proto) not in cur_keys)
    return DriftResult(added=added, removed=removed)
