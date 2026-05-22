"""Audit log retention policy — trim entries older than a given age."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List


@dataclass
class RetentionPolicy:
    max_age_days: int = 30
    max_entries: int = 10_000

    def __post_init__(self) -> None:
        if self.max_age_days < 1:
            raise ValueError("max_age_days must be >= 1")
        if self.max_entries < 1:
            raise ValueError("max_entries must be >= 1")

    def cutoff(self) -> datetime:
        return datetime.now(tz=timezone.utc) - timedelta(days=self.max_age_days)


def apply_retention(audit_path: Path, policy: RetentionPolicy) -> int:
    """Remove audit entries that violate *policy*.

    Returns the number of entries that were removed.
    """
    if not audit_path.exists():
        return 0

    raw = audit_path.read_text(encoding="utf-8").strip()
    if not raw:
        return 0

    entries: List[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # skip corrupt lines

    cutoff = policy.cutoff()
    before = len(entries)

    # Filter by age
    def _is_fresh(entry: dict) -> bool:
        ts = entry.get("timestamp")
        if not ts:
            return True
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt >= cutoff
        except ValueError:
            return True

    entries = [e for e in entries if _is_fresh(e)]

    # Trim to max_entries (keep newest)
    if len(entries) > policy.max_entries:
        entries = entries[-policy.max_entries :]

    removed = before - len(entries)

    lines = [json.dumps(e, separators=(",", ":")) for e in entries]
    audit_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    return removed
