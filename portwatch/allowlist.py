"""Allowlist: ports/processes that are always considered safe and suppressed from alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from portwatch.scanner import PortEntry


@dataclass
class AllowRule:
    port: Optional[int] = None
    proto: Optional[str] = None
    process: Optional[str] = None

    def matches(self, entry: PortEntry) -> bool:
        if self.port is not None and entry.port != self.port:
            return False
        if self.proto is not None and entry.proto != self.proto:
            return False
        if self.process is not None:
            proc = entry.process or ""
            if self.process not in proc:
                return False
        return True

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "port": self.port,
            "proto": self.proto,
            "process": self.process,
        }.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "AllowRule":
        return cls(
            port=data.get("port"),
            proto=data.get("proto"),
            process=data.get("process"),
        )


@dataclass
class Allowlist:
    rules: List[AllowRule] = field(default_factory=list)

    def is_allowed(self, entry: PortEntry) -> bool:
        return any(r.matches(entry) for r in self.rules)

    def filter_allowed(self, entries: List[PortEntry]) -> List[PortEntry]:
        return [e for e in entries if not self.is_allowed(e)]

    def to_dict(self) -> dict:
        return {"rules": [r.to_dict() for r in self.rules]}

    @classmethod
    def from_dict(cls, data: dict) -> "Allowlist":
        rules = [AllowRule.from_dict(r) for r in data.get("rules", [])]
        return cls(rules=rules)
