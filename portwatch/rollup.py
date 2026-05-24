"""Rollup: aggregate change events into period summaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict

from portwatch.alerter import ChangeEvent


@dataclass
class RollupBucket:
    period_start: datetime
    period_end: datetime
    opened: List[ChangeEvent] = field(default_factory=list)
    closed: List[ChangeEvent] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.opened) + len(self.closed)

    def is_empty(self) -> bool:
        return self.total == 0

    def summary(self) -> str:
        start = self.period_start.strftime("%Y-%m-%d %H:%M:%S")
        end = self.period_end.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"[{start} -> {end}] "
            f"+{len(self.opened)} opened, -{len(self.closed)} closed "
            f"({self.total} total)"
        )

    def to_dict(self) -> Dict:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "opened": [str(e) for e in self.opened],
            "closed": [str(e) for e in self.closed],
            "total": self.total,
        }


def rollup_events(
    events: List[ChangeEvent],
    period_seconds: int = 3600,
    reference: datetime | None = None,
) -> List[RollupBucket]:
    """Group events into fixed-width time buckets.

    Args:
        events: list of ChangeEvent instances (must have a .timestamp attribute).
        period_seconds: bucket width in seconds (default 1 hour).
        reference: epoch anchor for bucket boundaries; defaults to UTC now.

    Returns:
        List of RollupBucket, sorted by period_start, non-empty buckets only.
    """
    if period_seconds <= 0:
        raise ValueError("period_seconds must be positive")
    if not events:
        return []

    ref = reference or datetime.now(timezone.utc)
    ref_ts = ref.timestamp()

    buckets: Dict[int, RollupBucket] = {}

    for ev in events:
        ts = ev.timestamp.timestamp() if hasattr(ev.timestamp, "timestamp") else float(ev.timestamp)
        offset = ts - ref_ts
        bucket_idx = int(offset // period_seconds)
        if bucket_idx not in buckets:
            bstart = datetime.fromtimestamp(ref_ts + bucket_idx * period_seconds, tz=timezone.utc)
            bend = datetime.fromtimestamp(ref_ts + (bucket_idx + 1) * period_seconds, tz=timezone.utc)
            buckets[bucket_idx] = RollupBucket(period_start=bstart, period_end=bend)
        bucket = buckets[bucket_idx]
        if ev.kind == "opened":
            bucket.opened.append(ev)
        else:
            bucket.closed.append(ev)

    return [buckets[k] for k in sorted(buckets) if not buckets[k].is_empty()]
