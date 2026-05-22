"""Tag-based labelling for port entries and change events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Dict, Any

from portwatch.scanner import PortEntry


@dataclass(frozen=True)
class TagRule:
    """Assigns a tag when a port entry matches given criteria."""
    tag: str
    port: int | None = None
    proto: str | None = None
    process: str | None = None

    def matches(self, entry: PortEntry) -> bool:
        if self.port is not None and entry.port != self.port:
            return False
        if self.proto is not None and entry.proto != self.proto:
            return False
        if self.process is not None:
            if entry.process is None:
                return False
            if self.process not in entry.process:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"tag": self.tag}
        if self.port is not None:
            d["port"] = self.port
        if self.proto is not None:
            d["proto"] = self.proto
        if self.process is not None:
            d["process"] = self.process
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagRule":
        return cls(
            tag=data["tag"],
            port=data.get("port"),
            proto=data.get("proto"),
            process=data.get("process"),
        )


@dataclass
class TagSet:
    """Collection of TagRules; resolves tags for a given PortEntry."""
    rules: List[TagRule] = field(default_factory=list)

    def resolve(self, entry: PortEntry) -> FrozenSet[str]:
        """Return all tags whose rules match *entry*."""
        return frozenset(r.tag for r in self.rules if r.matches(entry))

    def to_dict(self) -> Dict[str, Any]:
        return {"rules": [r.to_dict() for r in self.rules]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagSet":
        rules = [TagRule.from_dict(r) for r in data.get("rules", [])]
        return cls(rules=rules)
