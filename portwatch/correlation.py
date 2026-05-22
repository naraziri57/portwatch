"""Correlate related change events (e.g. a port closing then re-opening
on the same process) into a named pattern."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from portwatch.alerter import ChangeEvent


@dataclass
class CorrelatedGroup:
    """A set of events that share a common correlation pattern."""

    pattern: str  # e.g. "restart", "port-swap", "process-change"
    events: List[ChangeEvent] = field(default_factory=list)

    def summary(self) -> str:
        ports = sorted({e.entry.port for e in self.events})
        return f"[{self.pattern}] ports={ports} events={len(self.events)}"


def _same_process(a: ChangeEvent, b: ChangeEvent) -> bool:
    return (
        a.entry.process is not None
        and b.entry.process is not None
        and a.entry.process == b.entry.process
    )


def _same_port(a: ChangeEvent, b: ChangeEvent) -> bool:
    return a.entry.port == b.entry.port and a.entry.proto == b.entry.proto


def correlate_events(events: List[ChangeEvent]) -> List[CorrelatedGroup]:
    """Group a flat list of ChangeEvents into correlated patterns.

    Rules (applied in order, first match wins per pair):
    - "restart"    : same port+proto, one OPENED + one CLOSED, same process
    - "port-swap"  : same process, different ports, mix of OPENED/CLOSED
    - "process-change": same port+proto, different processes
    - remaining events are returned as individual "unclassified" groups
    """
    used: set[int] = set()
    groups: List[CorrelatedGroup] = []

    opened = [e for e in events if e.kind == "OPENED"]
    closed = [e for e in events if e.kind == "CLOSED"]

    # restart: same port, same process, one open + one close
    for o in opened:
        for c in closed:
            if id(o) in used or id(c) in used:
                continue
            if _same_port(o, c) and _same_process(o, c):
                groups.append(CorrelatedGroup(pattern="restart", events=[c, o]))
                used.add(id(o))
                used.add(id(c))

    # port-swap: same process, different ports
    for o in opened:
        for c in closed:
            if id(o) in used or id(c) in used:
                continue
            if not _same_port(o, c) and _same_process(o, c):
                groups.append(CorrelatedGroup(pattern="port-swap", events=[c, o]))
                used.add(id(o))
                used.add(id(c))

    # process-change: same port, different processes
    for o in opened:
        for c in closed:
            if id(o) in used or id(c) in used:
                continue
            if _same_port(o, c) and not _same_process(o, c):
                groups.append(CorrelatedGroup(pattern="process-change", events=[c, o]))
                used.add(id(o))
                used.add(id(c))

    # leftovers
    for e in events:
        if id(e) not in used:
            groups.append(CorrelatedGroup(pattern="unclassified", events=[e]))

    return groups
