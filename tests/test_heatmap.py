"""Tests for portwatch.heatmap."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.heatmap import Heatmap, HeatmapCell, load_heatmap, save_heatmap
from portwatch.scanner import PortEntry


def _entry() -> PortEntry:
    return PortEntry(proto="tcp", port=8080, address="0.0.0.0", process="app")


def _event(ts: str = "2024-06-10T14:30:00") -> ChangeEvent:
    return ChangeEvent(kind="opened", entry=_entry(), timestamp=ts)


# --- HeatmapCell ---

class TestHeatmapCell:
    def test_to_dict_roundtrip(self):
        cell = HeatmapCell(day=2, hour=15, count=7)
        assert HeatmapCell.from_dict(cell.to_dict()) == cell

    def test_defaults_count_zero(self):
        cell = HeatmapCell(day=0, hour=0)
        assert cell.count == 0


# --- Heatmap.record ---

class TestHeatmapRecord:
    def test_empty_by_default(self):
        h = Heatmap()
        assert h.get(0, 0) == 0

    def test_record_increments_count(self):
        h = Heatmap()
        dt = datetime(2024, 6, 10, 14, 0)  # Monday=0, hour=14
        h.record(dt)
        assert h.get(dt.weekday(), 14) == 1

    def test_record_twice_accumulates(self):
        h = Heatmap()
        dt = datetime(2024, 6, 10, 9, 0)
        h.record(dt)
        h.record(dt)
        assert h.get(dt.weekday(), 9) == 2

    def test_record_event_uses_timestamp(self):
        h = Heatmap()
        ev = _event("2024-06-10T14:30:00")  # Monday 14:00
        h.record_event(ev)
        assert h.get(0, 14) == 1  # Monday=0

    def test_different_slots_independent(self):
        h = Heatmap()
        h.record(datetime(2024, 6, 10, 8, 0))
        h.record(datetime(2024, 6, 11, 8, 0))
        assert h.get(0, 8) == 1
        assert h.get(1, 8) == 1


# --- peak_hour ---

class TestPeakHour:
    def test_none_when_empty(self):
        assert Heatmap().peak_hour() is None

    def test_returns_highest_cell(self):
        h = Heatmap()
        for _ in range(3):
            h.record(datetime(2024, 6, 10, 14, 0))  # Monday 14
        h.record(datetime(2024, 6, 11, 9, 0))       # Tuesday 9
        assert h.peak_hour() == (0, 14)


# --- cells ---

def test_cells_sorted_by_day_then_hour():
    h = Heatmap()
    h.record(datetime(2024, 6, 12, 10, 0))  # Wednesday
    h.record(datetime(2024, 6, 10, 14, 0))  # Monday
    cells = h.cells()
    days = [c.day for c in cells]
    assert days == sorted(days)


# --- serialization ---

class TestHeatmapSerialization:
    def test_roundtrip(self):
        h = Heatmap()
        h.record(datetime(2024, 6, 10, 14, 0))
        h2 = Heatmap.from_dict(h.to_dict())
        assert h2.get(0, 14) == 1

    def test_save_load(self, tmp_path: Path):
        h = Heatmap()
        h.record(datetime(2024, 6, 10, 14, 0))
        p = tmp_path / "heatmap.json"
        save_heatmap(h, p)
        h2 = load_heatmap(p)
        assert h2.get(0, 14) == 1

    def test_load_missing_returns_empty(self, tmp_path: Path):
        h = load_heatmap(tmp_path / "missing.json")
        assert h.peak_hour() is None

    def test_save_is_valid_json(self, tmp_path: Path):
        h = Heatmap()
        h.record(datetime(2024, 6, 10, 8, 0))
        p = tmp_path / "heatmap.json"
        save_heatmap(h, p)
        data = json.loads(p.read_text())
        assert "grid" in data
