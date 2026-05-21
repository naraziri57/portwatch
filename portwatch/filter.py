"""Port filtering rules — lets users ignore certain ports/protocols from alerts."""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from portwatch.scanner import PortEntry


@dataclass
class FilterRule:
    """A single ignore rule. Supports wildcards in process names."""

    port: int | None = None          # None means match any port
    proto: str | None = None         # 'tcp', 'udp', or None for any
    process: str | None = None       # glob pattern, e.g. 'nginx' or '*python*'

    def matches(self, entry: PortEntry) -> bool:
        if self.port is not None and entry.port != self.port:
            return False
        if self.proto is not None and entry.proto.lower() != self.proto.lower():
            return False
        if self.process is not None:
            proc = entry.process or ""
            if not fnmatch.fnmatch(proc, self.process):
                return False
        return True

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "port": self.port,
            "proto": self.proto,
            "process": self.process,
        }.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "FilterRule":
        return cls(
            port=data.get("port"),
            proto=data.get("proto"),
            process=data.get("process"),
        )


@dataclass
class FilterSet:
    """Collection of ignore rules loaded from a JSON config file."""

    rules: list[FilterRule] = field(default_factory=list)

    def should_ignore(self, entry: PortEntry) -> bool:
        return any(rule.matches(entry) for rule in self.rules)

    def apply(self, entries: Iterable[PortEntry]) -> list[PortEntry]:
        """Return entries that are NOT matched by any ignore rule."""
        return [e for e in entries if not self.should_ignore(e)]

    def save(self, path: Path | str) -> None:
        Path(path).write_text(
            json.dumps([r.to_dict() for r in self.rules], indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path | str) -> "FilterSet":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(rules=[FilterRule.from_dict(d) for d in raw])

    @classmethod
    def empty(cls) -> "FilterSet":
        return cls(rules=[])
