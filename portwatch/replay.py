"""Replay recorded audit events for testing and analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

from portwatch.audit import AuditEntry
from portwatch.alerter import ChangeEvent


@dataclass
class ReplayOptions:
    speed: float = 1.0          # multiplier; 0 = instant
    start_index: int = 0
    end_index: Optional[int] = None
    filter_kind: Optional[str] = None  # "opened" | "closed" | None

    def __post_init__(self) -> None:
        if self.speed < 0:
            raise ValueError("speed must be >= 0")
        if self.start_index < 0:
            raise ValueError("start_index must be >= 0")


@dataclass
class ReplayResult:
    replayed: int = 0
    skipped: int = 0
    events: List[ChangeEvent] = field(default_factory=list)


def _entry_to_event(entry: AuditEntry) -> ChangeEvent:
    """Convert a stored AuditEntry back into a ChangeEvent."""
    return ChangeEvent(kind=entry.kind, port=entry.port)


def replay_entries(
    entries: Iterable[AuditEntry],
    handler: Callable[[ChangeEvent], None],
    options: Optional[ReplayOptions] = None,
) -> ReplayResult:
    """Feed audit entries through *handler* as ChangeEvents.

    Returns a ReplayResult describing what happened.
    """
    opts = options or ReplayOptions()
    result = ReplayResult()

    all_entries = list(entries)
    end = opts.end_index if opts.end_index is not None else len(all_entries)
    window = all_entries[opts.start_index : end]

    for entry in window:
        if opts.filter_kind and entry.kind != opts.filter_kind:
            result.skipped += 1
            continue
        event = _entry_to_event(entry)
        handler(event)
        result.events.append(event)
        result.replayed += 1

    return result
