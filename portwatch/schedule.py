"""Flexible scan scheduling with cron-like time windows."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from typing import List, Optional


@dataclass
class ScheduleWindow:
    """A named time window during which scanning is active."""

    name: str
    start: dt_time  # e.g. time(8, 0)
    end: dt_time    # e.g. time(18, 0)
    days: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon

    def __post_init__(self) -> None:
        if not self.days:
            raise ValueError("days must not be empty")
        for d in self.days:
            if d not in range(7):
                raise ValueError(f"invalid day {d!r}; must be 0-6")

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if *at* (default: now) falls inside this window."""
        now = at or datetime.now()
        if now.weekday() not in self.days:
            return False
        return self.start <= now.time() <= self.end

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "days": self.days,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleWindow":
        start = dt_time(*map(int, data["start"].split(":")))
        end = dt_time(*map(int, data["end"].split(":")))
        return cls(name=data["name"], start=start, end=end, days=data.get("days", list(range(7))))


@dataclass
class ScanSchedule:
    """Collection of windows; scanning runs when ANY window is active."""

    windows: List[ScheduleWindow] = field(default_factory=list)
    default_active: bool = True  # active when no windows defined

    def is_active(self, at: Optional[datetime] = None) -> bool:
        if not self.windows:
            return self.default_active
        return any(w.is_active(at) for w in self.windows)

    def next_check_delay(self, interval: float, at: Optional[datetime] = None) -> float:
        """Return *interval* when active, or seconds until next minute when idle."""
        if self.is_active(at):
            return interval
        return 60.0  # re-evaluate each minute while outside windows
