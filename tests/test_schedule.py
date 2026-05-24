"""Tests for portwatch.schedule."""

import pytest
from datetime import datetime, time as dt_time

from portwatch.schedule import ScheduleWindow, ScanSchedule


# ---------------------------------------------------------------------------
# ScheduleWindow validation
# ---------------------------------------------------------------------------

def test_empty_days_raises():
    with pytest.raises(ValueError, match="days must not be empty"):
        ScheduleWindow("x", dt_time(8), dt_time(18), days=[])


def test_invalid_day_raises():
    with pytest.raises(ValueError, match="invalid day"):
        ScheduleWindow("x", dt_time(8), dt_time(18), days=[7])


# ---------------------------------------------------------------------------
# ScheduleWindow.is_active
# ---------------------------------------------------------------------------

_WEEKDAY_NOON = datetime(2024, 1, 8, 12, 0)   # Monday
_WEEKDAY_EARLY = datetime(2024, 1, 8, 6, 0)   # Monday 06:00
_WEEKEND_NOON = datetime(2024, 1, 6, 12, 0)   # Saturday


def _business_hours() -> ScheduleWindow:
    return ScheduleWindow("biz", dt_time(8, 0), dt_time(18, 0), days=list(range(5)))


def test_active_within_window():
    assert _business_hours().is_active(_WEEKDAY_NOON) is True


def test_inactive_before_start():
    assert _business_hours().is_active(_WEEKDAY_EARLY) is False


def test_inactive_on_weekend():
    assert _business_hours().is_active(_WEEKEND_NOON) is False


# ---------------------------------------------------------------------------
# ScheduleWindow serialisation
# ---------------------------------------------------------------------------

def test_to_dict_roundtrip():
    w = _business_hours()
    assert ScheduleWindow.from_dict(w.to_dict()).name == w.name


def test_from_dict_parses_times():
    w = ScheduleWindow.from_dict({"name": "n", "start": "09:30", "end": "17:00"})
    assert w.start == dt_time(9, 30)
    assert w.end == dt_time(17, 0)


# ---------------------------------------------------------------------------
# ScanSchedule
# ---------------------------------------------------------------------------

def test_no_windows_defaults_to_active():
    assert ScanSchedule().is_active() is True


def test_no_windows_default_false():
    assert ScanSchedule(default_active=False).is_active() is False


def test_active_when_any_window_matches():
    s = ScanSchedule(windows=[_business_hours()])
    assert s.is_active(_WEEKDAY_NOON) is True


def test_inactive_when_no_window_matches():
    s = ScanSchedule(windows=[_business_hours()])
    assert s.is_active(_WEEKEND_NOON) is False


def test_next_check_delay_active_returns_interval():
    s = ScanSchedule(windows=[_business_hours()])
    assert s.next_check_delay(30.0, _WEEKDAY_NOON) == 30.0


def test_next_check_delay_inactive_returns_sixty():
    s = ScanSchedule(windows=[_business_hours()])
    assert s.next_check_delay(30.0, _WEEKEND_NOON) == 60.0
