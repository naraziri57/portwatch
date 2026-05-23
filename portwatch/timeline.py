"""Timeline: ordered history of port events with time-range querying."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from portwatch.alerter import ChangeEvent


@dataclass
class TimelineEntry:
    timestamp: datetime
    kind: str          # "opened" | "closed"
    port: int
    proto: str
    process: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "kind": self.kind,
            "port": self.port,
            "proto": self.proto,
            "process": self.process,
        }

    @staticmethod
    def from_dict(d: dict) -> "TimelineEntry":
        return TimelineEntry(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            kind=d["kind"],
            port=d["port"],
            proto=d["proto"],
            process=d.get("process"),
        )

    @staticmethod
    def from_event(event: ChangeEvent) -> "TimelineEntry":
        return TimelineEntry(
            timestamp=datetime.now(tz=timezone.utc),
            kind=event.kind,
            port=event.entry.port,
            proto=event.entry.proto,
            process=event.entry.process,
        )


def append_events(path: Path, events: List[ChangeEvent]) -> None:
    """Append new events to the timeline log file."""
    entries: List[dict] = []
    if path.exists():
        entries = json.loads(path.read_text())
    for ev in events:
        entries.append(TimelineEntry.from_event(ev).to_dict())
    path.write_text(json.dumps(entries, indent=2))


def load_timeline(path: Path) -> List[TimelineEntry]:
    """Load all timeline entries from disk."""
    if not path.exists():
        return []
    return [TimelineEntry.from_dict(d) for d in json.loads(path.read_text())]


def query_range(
    entries: List[TimelineEntry],
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> List[TimelineEntry]:
    """Filter entries to a time range (both bounds inclusive, UTC-aware)."""
    result = entries
    if since is not None:
        result = [e for e in result if e.timestamp >= since]
    if until is not None:
        result = [e for e in result if e.timestamp <= until]
    return result
