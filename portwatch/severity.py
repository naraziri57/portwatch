"""Severity classification for port change events."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from portwatch.alerter import ChangeEvent


class Level(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Ports that warrant elevated severity when opened unexpectedly.
_SENSITIVE_PORTS = {
    22,    # SSH
    23,    # Telnet
    3389,  # RDP
    5900,  # VNC
    4444,  # common reverse-shell
    1337,
}

_PRIVILEGED_THRESHOLD = 1024


@dataclass
class SeverityRule:
    """Maps a condition to a severity level."""
    ports: list[int] = field(default_factory=list)
    level: Level = Level.MEDIUM

    def matches(self, event: ChangeEvent) -> bool:
        if self.ports:
            return event.entry.port in self.ports
        return False

    def to_dict(self) -> dict:
        return {"ports": list(self.ports), "level": self.level.value}

    @classmethod
    def from_dict(cls, data: dict) -> "SeverityRule":
        return cls(
            ports=data.get("ports", []),
            level=Level(data.get("level", Level.MEDIUM.value)),
        )


def classify(event: ChangeEvent, rules: Optional[list[SeverityRule]] = None) -> Level:
    """Return a severity Level for a ChangeEvent.

    Custom rules are checked first (first match wins).  Falls back to
    built-in heuristics when no rule matches.
    """
    for rule in (rules or []):
        if rule.matches(event):
            return rule.level

    port = event.entry.port
    kind = event.kind  # "opened" | "closed"

    if kind == "opened":
        if port in _SENSITIVE_PORTS:
            return Level.CRITICAL
        if port < _PRIVILEGED_THRESHOLD:
            return Level.HIGH
        return Level.MEDIUM

    # closed events are generally informational
    if port in _SENSITIVE_PORTS:
        return Level.MEDIUM
    return Level.LOW
