"""Audit log: persists a rolling history of port change events."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from portwatch.alerter import ChangeEvent

DEFAULT_MAX_ENTRIES = 500


@dataclass
class AuditEntry:
    timestamp: str
    kind: str          # "opened" | "closed"
    proto: str
    port: int
    process: str | None

    @classmethod
    def from_event(cls, event: ChangeEvent) -> "AuditEntry":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            kind=event.kind,
            proto=event.entry.proto,
            port=event.entry.port,
            process=event.entry.process,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEntry":
        return cls(**d)


def append_events(
    path: Path | str,
    events: List[ChangeEvent],
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> None:
    """Append *events* to the audit log at *path*, trimming to *max_entries*."""
    path = Path(path)
    existing = load_audit(path)
    new_entries = [AuditEntry.from_event(e) for e in events]
    combined = existing + new_entries
    if len(combined) > max_entries:
        combined = combined[-max_entries:]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump([e.to_dict() for e in combined], fh, indent=2)


def load_audit(path: Path | str) -> List[AuditEntry]:
    """Return all audit entries from *path*, or [] if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open() as fh:
        raw = json.load(fh)
    return [AuditEntry.from_dict(d) for d in raw]


def clear_audit(path: Path | str) -> None:
    """Delete the audit log file if it exists."""
    path = Path(path)
    if path.exists():
        os.remove(path)
