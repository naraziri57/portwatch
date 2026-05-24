"""Track packet loss estimates per host based on reachability probe history."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


_DEFAULT_WINDOW = 20  # number of probes to keep per host


@dataclass
class LossStats:
    host: str
    window: int = _DEFAULT_WINDOW
    _results: Deque[bool] = field(default_factory=deque, repr=False)

    def __post_init__(self) -> None:
        if self.window < 1:
            raise ValueError("window must be >= 1")
        self._results = deque(maxlen=self.window)

    def record(self, reachable: bool) -> None:
        """Record one probe outcome (True = success, False = loss)."""
        self._results.append(reachable)

    @property
    def total_probes(self) -> int:
        return len(self._results)

    @property
    def loss_rate(self) -> float:
        """Return fraction of probes that were lost (0.0 – 1.0)."""
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if not r) / len(self._results)

    @property
    def loss_percent(self) -> float:
        return self.loss_rate * 100.0

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "total_probes": self.total_probes,
            "loss_rate": round(self.loss_rate, 4),
            "loss_percent": round(self.loss_percent, 2),
        }

    def __str__(self) -> str:
        return (
            f"{self.host}: {self.loss_percent:.1f}% loss "
            f"({self.total_probes} probes)"
        )


class PacketLossTracker:
    """Aggregate LossStats across multiple hosts."""

    def __init__(self, window: int = _DEFAULT_WINDOW) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        self._window = window
        self._hosts: Dict[str, LossStats] = {}

    def record(self, host: str, reachable: bool) -> None:
        if host not in self._hosts:
            self._hosts[host] = LossStats(host=host, window=self._window)
        self._hosts[host].record(reachable)

    def stats_for(self, host: str) -> LossStats | None:
        return self._hosts.get(host)

    def all_stats(self) -> list[LossStats]:
        return sorted(self._hosts.values(), key=lambda s: s.host)

    def hosts_above_threshold(self, threshold: float = 0.1) -> list[LossStats]:
        """Return hosts whose loss_rate exceeds *threshold* (0.0–1.0)."""
        return [s for s in self.all_stats() if s.loss_rate > threshold]
