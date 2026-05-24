"""Integration tests for the heatmap feature end-to-end."""
from datetime import datetime
from pathlib import Path

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.heatmap import Heatmap, load_heatmap, save_heatmap
from portwatch.scanner import PortEntry


def _entry(port: int = 8080) -> PortEntry:
    return PortEntry(proto="tcp", port=port, address="0.0.0.0", process="svc")


def _ev(ts: str, port: int = 8080) -> ChangeEvent:
    return ChangeEvent(kind="opened", entry=_entry(port), timestamp=ts)


class TestHeatmapLifecycle:
    def test_persist_and_reload(self, tmp_path: Path):
        h = Heatmap()
        h.record(datetime(2024, 6, 10, 10, 0))  # Monday 10:00
        h.record(datetime(2024, 6, 10, 10, 0))
        p = tmp_path / "hm.json"
        save_heatmap(h, p)
        h2 = load_heatmap(p)
        assert h2.get(0, 10) == 2

    def test_multiple_events_accumulate(self):
        h = Heatmap()
        events = [
            _ev("2024-06-10T08:00:00"),  # Mon 08
            _ev("2024-06-10T08:15:00"),  # Mon 08 again
            _ev("2024-06-11T20:00:00"),  # Tue 20
        ]
        for ev in events:
            h.record_event(ev)
        assert h.get(0, 8) == 2
        assert h.get(1, 20) == 1

    def test_peak_reflects_busiest_slot(self):
        h = Heatmap()
        for _ in range(5):
            h.record(datetime(2024, 6, 12, 22, 0))  # Wed 22
        h.record(datetime(2024, 6, 10, 8, 0))       # Mon 08 (only once)
        day, hour = h.peak_hour()
        assert day == 2  # Wednesday
        assert hour == 22

    def test_cells_count_matches_records(self):
        h = Heatmap()
        h.record(datetime(2024, 6, 10, 8, 0))
        h.record(datetime(2024, 6, 11, 9, 0))
        h.record(datetime(2024, 6, 11, 9, 0))
        cells = h.cells()
        total = sum(c.count for c in cells)
        assert total == 3

    def test_empty_heatmap_no_cells(self):
        h = Heatmap()
        assert h.cells() == []
        assert h.peak_hour() is None
