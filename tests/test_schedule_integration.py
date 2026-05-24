"""Integration tests: ScanSchedule drives watcher timing decisions."""

from datetime import datetime, time as dt_time

import pytest

from portwatch.schedule import ScanSchedule, ScheduleWindow


def _window(start: str, end: str, days=None) -> ScheduleWindow:
    s = dt_time(*map(int, start.split(":")))
    e = dt_time(*map(int, end.split(":")))
    return ScheduleWindow("w", s, e, days=days or list(range(7)))


class TestScheduleIntegration:
    def test_single_window_active(self):
        sched = ScanSchedule(windows=[_window("08:00", "18:00")])
        assert sched.is_active(datetime(2024, 3, 4, 12, 0)) is True

    def test_single_window_inactive(self):
        sched = ScanSchedule(windows=[_window("08:00", "18:00")])
        assert sched.is_active(datetime(2024, 3, 4, 20, 0)) is False

    def test_two_windows_cover_split_day(self):
        morning = _window("07:00", "12:00")
        afternoon = _window("13:00", "19:00")
        sched = ScanSchedule(windows=[morning, afternoon])
        assert sched.is_active(datetime(2024, 3, 4, 8, 0)) is True
        assert sched.is_active(datetime(2024, 3, 4, 12, 30)) is False
        assert sched.is_active(datetime(2024, 3, 4, 15, 0)) is True

    def test_delay_halved_when_active(self):
        sched = ScanSchedule(windows=[_window("00:00", "23:59")])
        delay = sched.next_check_delay(60.0, datetime(2024, 3, 4, 10, 0))
        assert delay == 60.0

    def test_delay_sixty_when_inactive(self):
        sched = ScanSchedule(windows=[_window("09:00", "17:00")])
        delay = sched.next_check_delay(30.0, datetime(2024, 3, 4, 3, 0))
        assert delay == 60.0

    def test_weekday_restriction_respected(self):
        weekdays_only = _window("08:00", "20:00", days=list(range(5)))
        sched = ScanSchedule(windows=[weekdays_only])
        saturday = datetime(2024, 1, 6, 12, 0)   # Saturday
        monday = datetime(2024, 1, 8, 12, 0)      # Monday
        assert sched.is_active(saturday) is False
        assert sched.is_active(monday) is True
