"""Periodic digest reporter: aggregates change events and formats a summary."""

from __future__ import annotations

import datetime
from collections import Counter
from dataclasses import dataclass, field
from typing import List

from portwatch.alerter import ChangeEvent


@dataclass
class DigestReport:
    events: List[ChangeEvent] = field(default_factory=list)
    generated_at: datetime.datetime = field(
        default_factory=datetime.datetime.utcnow
    )

    def add(self, event: ChangeEvent) -> None:
        self.events.append(event)

    @property
    def is_empty(self) -> bool:
        return len(self.events) == 0

    def summary(self) -> str:
        if self.is_empty:
            return "No changes detected."

        counts: Counter[str] = Counter(e.kind for e in self.events)
        lines = [
            f"Digest Report — {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"Total changes: {len(self.events)}",
        ]
        for kind, n in sorted(counts.items()):
            lines.append(f"  {kind}: {n}")
        lines.append("")
        lines.append("Details:")
        for ev in self.events:
            lines.append(f"  {ev}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Clear accumulated events (call after sending)."""
        self.events.clear()
        self.generated_at = datetime.datetime.utcnow()


def build_digest(events: List[ChangeEvent]) -> DigestReport:
    """Convenience: create a DigestReport pre-populated with *events*."""
    report = DigestReport()
    for ev in events:
        report.add(ev)
    return report
