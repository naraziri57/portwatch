"""Simple in-process metrics counters for portwatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class MetricsSnapshot:
    """Immutable snapshot of current metrics values."""
    scans_total: int
    scan_errors: int
    events_total: int
    events_by_kind: Dict[str, int]
    captured_at: str

    def to_dict(self) -> dict:
        return {
            "scans_total": self.scans_total,
            "scan_errors": self.scan_errors,
            "events_total": self.events_total,
            "events_by_kind": dict(self.events_by_kind),
            "captured_at": self.captured_at,
        }


@dataclass
class Metrics:
    """Mutable metrics registry; one instance per daemon run."""
    _scans_total: int = field(default=0, init=False)
    _scan_errors: int = field(default=0, init=False)
    _events_by_kind: Dict[str, int] = field(default_factory=dict, init=False)

    def record_scan(self) -> None:
        self._scans_total += 1

    def record_error(self) -> None:
        self._scan_errors += 1

    def record_event(self, kind: str) -> None:
        self._events_by_kind[kind] = self._events_by_kind.get(kind, 0) + 1

    @property
    def scans_total(self) -> int:
        return self._scans_total

    @property
    def scan_errors(self) -> int:
        return self._scan_errors

    @property
    def events_total(self) -> int:
        return sum(self._events_by_kind.values())

    def snapshot(self) -> MetricsSnapshot:
        now = datetime.now(tz=timezone.utc).isoformat()
        return MetricsSnapshot(
            scans_total=self._scans_total,
            scan_errors=self._scan_errors,
            events_total=self.events_total,
            events_by_kind=dict(self._events_by_kind),
            captured_at=now,
        )

    def reset(self) -> None:
        self._scans_total = 0
        self._scan_errors = 0
        self._events_by_kind.clear()


# Module-level default instance
_default: Optional[Metrics] = None


def get_metrics() -> Metrics:
    """Return the process-wide Metrics instance, creating it on first call."""
    global _default
    if _default is None:
        _default = Metrics()
    return _default
