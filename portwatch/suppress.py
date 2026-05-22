"""Suppression list: ignore specific ports/protos/processes from alerting."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from portwatch.scanner import PortEntry


@dataclass
class SuppressRule:
    port: int | None = None
    proto: str | None = None
    process: str | None = None

    def matches(self, entry: PortEntry) -> bool:
        if self.port is not None and entry.port != self.port:
            return False
        if self.proto is not None and entry.proto != self.proto:
            return False
        if self.process is not None and entry.process != self.process:
            return False
        return True

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "port": self.port,
            "proto": self.proto,
            "process": self.process,
        }.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "SuppressRule":
        return cls(
            port=data.get("port"),
            proto=data.get("proto"),
            process=data.get("process"),
        )


@dataclass
class SuppressList:
    rules: list[SuppressRule] = field(default_factory=list)

    def is_suppressed(self, entry: PortEntry) -> bool:
        return any(r.matches(entry) for r in self.rules)

    def filter_entries(self, entries: Iterable[PortEntry]) -> list[PortEntry]:
        return [e for e in entries if not self.is_suppressed(e)]

    def add(self, rule: SuppressRule) -> None:
        self.rules.append(rule)

    def to_dict(self) -> dict:
        return {"rules": [r.to_dict() for r in self.rules]}

    @classmethod
    def from_dict(cls, data: dict) -> "SuppressList":
        rules = [SuppressRule.from_dict(r) for r in data.get("rules", [])]
        return cls(rules=rules)


def load_suppress_list(path: Path) -> SuppressList:
    if not path.exists():
        return SuppressList()
    with path.open() as fh:
        data = json.load(fh)
    return SuppressList.from_dict(data)


def save_suppress_list(path: Path, suppress: SuppressList) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(suppress.to_dict(), fh, indent=2)
