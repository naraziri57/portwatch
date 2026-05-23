"""Enrichment pipeline: attach geo, tags, severity, and risk score to a ChangeEvent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from portwatch.alerter import ChangeEvent
from portwatch.geo import GeoInfo, resolve_hostname
from portwatch.tags import TagSet
from portwatch.severity import SeverityRule, Level
from portwatch.scoring import RiskScore, score_event


@dataclass
class EnrichedEvent:
    """A ChangeEvent with optional enrichment metadata attached."""

    event: ChangeEvent
    geo: Optional[GeoInfo] = None
    tags: List[str] = field(default_factory=list)
    level: str = Level.INFO
    score: Optional[RiskScore] = None

    def to_dict(self) -> dict:
        return {
            "event": {
                "kind": self.event.kind,
                "port": self.event.entry.port,
                "proto": self.event.entry.proto,
                "process": self.event.entry.process,
            },
            "geo": self.geo.to_dict() if self.geo else None,
            "tags": self.tags,
            "level": self.level,
            "score": self.score.to_dict() if self.score else None,
        }

    def __str__(self) -> str:
        parts = [str(self.event)]
        if self.tags:
            parts.append(f"tags=[{', '.join(self.tags)}]")
        parts.append(f"level={self.level}")
        if self.score:
            parts.append(f"risk={self.score.total()}")
        return " | ".join(parts)


def enrich(
    event: ChangeEvent,
    *,
    tagset: Optional[TagSet] = None,
    severity_rules: Optional[List[SeverityRule]] = None,
    resolve_geo: bool = False,
) -> EnrichedEvent:
    """Run an event through the enrichment pipeline."""
    enriched = EnrichedEvent(event=event)

    if resolve_geo and event.entry.address:
        try:
            enriched.geo = resolve_hostname(event.entry.address)
        except Exception:
            pass

    if tagset is not None:
        enriched.tags = tagset.tags_for(event.entry)

    resolved_level = Level.INFO
    if severity_rules:
        for rule in severity_rules:
            if rule.matches(event.entry):
                resolved_level = rule.level
                break
    enriched.level = resolved_level

    enriched.score = score_event(event, level=resolved_level)

    return enriched
