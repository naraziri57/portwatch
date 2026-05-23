"""Quarantine list: ports/processes that are temporarily silenced from alerts."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from portwatch.scanner import PortEntry


@dataclass
class QuarantineEntry:
    port: int
    proto: str
    process: Optional[str]
    expires_at: float  # unix timestamp; 0 means never
    reason: str = ""

    def is_expired(self) -> bool:
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    def matches(self, entry: PortEntry) -> bool:
        if self.port != entry.port:
            return False
        if self.proto != entry.proto:
            return False
        if self.process is not None and self.process != entry.process:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "process": self.process,
            "expires_at": self.expires_at,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuarantineEntry":
        return cls(
            port=int(d["port"]),
            proto=str(d["proto"]),
            process=d.get("process"),
            expires_at=float(d.get("expires_at", 0)),
            reason=str(d.get("reason", "")),
        )


@dataclass
class Quarantine:
    _entries: List[QuarantineEntry] = field(default_factory=list)

    def add(self, entry: QuarantineEntry) -> None:
        self._entries.append(entry)

    def is_quarantined(self, port_entry: PortEntry) -> bool:
        """Return True if port_entry is covered by a non-expired quarantine rule."""
        self._purge_expired()
        return any(e.matches(port_entry) for e in self._entries)

    def active_entries(self) -> List[QuarantineEntry]:
        self._purge_expired()
        return list(self._entries)

    def _purge_expired(self) -> None:
        self._entries = [e for e in self._entries if not e.is_expired()]

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))

    @classmethod
    def load(cls, path: Path) -> "Quarantine":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        entries = [QuarantineEntry.from_dict(d) for d in data]
        q = cls(entries)
        q._purge_expired()
        return q
