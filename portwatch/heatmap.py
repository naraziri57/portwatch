"""Port activity heatmap — tracks event frequency by hour-of-day and day-of-week."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from portwatch.alerter import ChangeEvent

_HOURS = 24
_DAYS = 7


@dataclass
class HeatmapCell:
    day: int   # 0=Monday … 6=Sunday
    hour: int  # 0-23
    count: int = 0

    def to_dict(self) -> dict:
        return {"day": self.day, "hour": self.hour, "count": self.count}

    @classmethod
    def from_dict(cls, d: dict) -> "HeatmapCell":
        return cls(day=d["day"], hour=d["hour"], count=d["count"])


@dataclass
class Heatmap:
    """Accumulates event counts indexed by (weekday, hour)."""
    _grid: Dict[str, int] = field(default_factory=dict)

    @staticmethod
    def _key(day: int, hour: int) -> str:
        return f"{day}:{hour}"

    def record(self, ts: datetime) -> None:
        key = self._key(ts.weekday(), ts.hour)
        self._grid[key] = self._grid.get(key, 0) + 1

    def record_event(self, event: ChangeEvent) -> None:
        self.record(datetime.fromisoformat(event.timestamp))

    def get(self, day: int, hour: int) -> int:
        return self._grid.get(self._key(day, hour), 0)

    def peak_hour(self) -> tuple[int, int] | None:
        """Return (day, hour) with the highest count, or None if empty."""
        if not self._grid:
            return None
        key = max(self._grid, key=lambda k: self._grid[k])
        day, hour = key.split(":")
        return int(day), int(hour)

    def cells(self) -> List[HeatmapCell]:
        result = []
        for key, count in self._grid.items():
            day, hour = key.split(":")
            result.append(HeatmapCell(day=int(day), hour=int(hour), count=count))
        return sorted(result, key=lambda c: (c.day, c.hour))

    def to_dict(self) -> dict:
        return {"grid": self._grid}

    @classmethod
    def from_dict(cls, d: dict) -> "Heatmap":
        obj = cls()
        obj._grid = dict(d.get("grid", {}))
        return obj


def save_heatmap(heatmap: Heatmap, path: Path) -> None:
    path.write_text(json.dumps(heatmap.to_dict(), indent=2))


def load_heatmap(path: Path) -> Heatmap:
    if not path.exists():
        return Heatmap()
    return Heatmap.from_dict(json.loads(path.read_text()))
