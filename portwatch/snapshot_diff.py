"""Structured diff between two port snapshots with severity and grouping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Tuple

from portwatch.scanner import PortEntry
from portwatch.severity import Level, SeverityRule


@dataclass(frozen=True)
class PortDiff:
    """A single port-level change between two snapshots."""

    kind: str  # 'opened' | 'closed'
    entry: PortEntry
    level: str = Level.INFO

    def __str__(self) -> str:
        arrow = "+" if self.kind == "opened" else "-"
        return f"[{self.level.upper()}] {arrow} {self.entry}"


@dataclass
class SnapshotDiff:
    """Full diff result between two snapshots."""

    opened: List[PortDiff] = field(default_factory=list)
    closed: List[PortDiff] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.opened and not self.closed

    @property
    def all_changes(self) -> List[PortDiff]:
        return self.opened + self.closed

    def summary(self) -> str:
        if self.is_empty:
            return "No changes detected."
        lines = []
        for d in self.opened:
            lines.append(str(d))
        for d in self.closed:
            lines.append(str(d))
        return "\n".join(lines)


def compute_diff(
    before: FrozenSet[PortEntry],
    after: FrozenSet[PortEntry],
    severity_rules: List[SeverityRule] | None = None,
) -> SnapshotDiff:
    """Compute opened/closed ports between two snapshots.

    Optionally applies severity rules to classify each change.
    """
    rules = severity_rules or []
    diff = SnapshotDiff()

    for entry in after - before:
        level = _resolve_level(entry, "opened", rules)
        diff.opened.append(PortDiff(kind="opened", entry=entry, level=level))

    for entry in before - after:
        level = _resolve_level(entry, "closed", rules)
        diff.closed.append(PortDiff(kind="closed", entry=entry, level=level))

    diff.opened.sort(key=lambda d: (d.entry.port, d.entry.proto))
    diff.closed.sort(key=lambda d: (d.entry.port, d.entry.proto))
    return diff


def _resolve_level(
    entry: PortEntry, kind: str, rules: List[SeverityRule]
) -> str:
    from portwatch.alerter import ChangeEvent

    ev = ChangeEvent(kind=kind, entry=entry)
    for rule in rules:
        if rule.matches(ev):
            return rule.level
    return Level.INFO
