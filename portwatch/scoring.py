"""Risk scoring for port change events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from portwatch.alerter import ChangeEvent
from portwatch.severity import Level

# Base scores per severity level
_LEVEL_SCORES: Dict[str, int] = {
    Level.LOW: 10,
    Level.MEDIUM: 30,
    Level.HIGH: 60,
    Level.CRITICAL: 100,
}

# Extra weight for well-known sensitive ports
_SENSITIVE_PORTS = {22, 23, 3306, 5432, 6379, 27017, 2375, 2376}
_SENSITIVE_BONUS = 20

# Multiplier for "opened" vs "closed" events
_KIND_MULTIPLIER = {"opened": 1.5, "closed": 1.0}


@dataclass
class RiskScore:
    event: ChangeEvent
    base: int
    bonus: int
    multiplier: float

    @property
    def total(self) -> int:
        return int((self.base + self.bonus) * self.multiplier)

    def to_dict(self) -> dict:
        return {
            "port": self.event.entry.port,
            "proto": self.event.entry.proto,
            "kind": self.event.kind,
            "base": self.base,
            "bonus": self.bonus,
            "multiplier": self.multiplier,
            "total": self.total,
        }

    def __str__(self) -> str:
        return (
            f"[{self.event.kind.upper()}] "
            f"{self.event.entry.proto}:{self.event.entry.port} "
            f"score={self.total}"
        )


def score_event(event: ChangeEvent, level: str = Level.MEDIUM) -> RiskScore:
    """Compute a risk score for a single ChangeEvent."""
    base = _LEVEL_SCORES.get(level, _LEVEL_SCORES[Level.MEDIUM])
    bonus = _SENSITIVE_BONUS if event.entry.port in _SENSITIVE_PORTS else 0
    multiplier = _KIND_MULTIPLIER.get(event.kind, 1.0)
    return RiskScore(event=event, base=base, bonus=bonus, multiplier=multiplier)


def score_events(events: List[ChangeEvent], level: str = Level.MEDIUM) -> List[RiskScore]:
    """Score a list of events, sorted highest total first."""
    scores = [score_event(e, level) for e in events]
    scores.sort(key=lambda s: s.total, reverse=True)
    return scores


def aggregate_score(scores: List[RiskScore]) -> int:
    """Return the sum of all individual scores (capped at 1000)."""
    return min(sum(s.total for s in scores), 1000)
