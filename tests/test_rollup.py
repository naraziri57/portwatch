"""Tests for portwatch.rollup."""
from datetime import datetime, timezone, timedelta

import pytest

from portwatch.rollup import RollupBucket, rollup_events
from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent


def _ts(offset_seconds: float = 0.0) -> datetime:
    base = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=offset_seconds)


def _ev(kind: str, port: int = 8080, offset: float = 0.0) -> ChangeEvent:
    entry = PortEntry(port=port, proto="tcp", address="0.0.0.0", process="app")
    return ChangeEvent(kind=kind, entry=entry, timestamp=_ts(offset))


# ── RollupBucket unit tests ──────────────────────────────────────────────────

class TestRollupBucket:
    def _bucket(self):
        return RollupBucket(period_start=_ts(0), period_end=_ts(3600))

    def test_empty_by_default(self):
        assert self._bucket().is_empty()

    def test_total_counts_both_sides(self):
        b = self._bucket()
        b.opened.append(_ev("opened"))
        b.closed.append(_ev("closed"))
        assert b.total == 2

    def test_summary_contains_period(self):
        b = self._bucket()
        b.opened.append(_ev("opened"))
        s = b.summary()
        assert "2024-06-01" in s

    def test_summary_contains_counts(self):
        b = self._bucket()
        b.opened.append(_ev("opened"))
        s = b.summary()
        assert "+1 opened" in s
        assert "-0 closed" in s

    def test_to_dict_has_required_keys(self):
        b = self._bucket()
        b.opened.append(_ev("opened"))
        d = b.to_dict()
        assert "period_start" in d
        assert "period_end" in d
        assert "opened" in d
        assert "closed" in d
        assert "total" in d

    def test_to_dict_total_matches(self):
        b = self._bucket()
        b.opened.append(_ev("opened"))
        b.closed.append(_ev("closed"))
        assert b.to_dict()["total"] == 2


# ── rollup_events tests ──────────────────────────────────────────────────────

class TestRollupEvents:
    REF = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_empty_input_returns_empty(self):
        assert rollup_events([], reference=self.REF) == []

    def test_single_event_one_bucket(self):
        events = [_ev("opened", offset=60)]
        buckets = rollup_events(events, period_seconds=3600, reference=self.REF)
        assert len(buckets) == 1

    def test_two_events_same_period_one_bucket(self):
        events = [_ev("opened", port=80, offset=100), _ev("closed", port=443, offset=200)]
        buckets = rollup_events(events, period_seconds=3600, reference=self.REF)
        assert len(buckets) == 1
        assert buckets[0].total == 2

    def test_events_in_different_periods_split(self):
        events = [_ev("opened", offset=100), _ev("opened", offset=4000)]
        buckets = rollup_events(events, period_seconds=3600, reference=self.REF)
        assert len(buckets) == 2

    def test_opened_and_closed_routed_correctly(self):
        events = [_ev("opened", offset=10), _ev("closed", offset=20)]
        buckets = rollup_events(events, period_seconds=3600, reference=self.REF)
        assert len(buckets[0].opened) == 1
        assert len(buckets[0].closed) == 1

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            rollup_events([_ev("opened")], period_seconds=0)

    def test_buckets_sorted_by_start(self):
        events = [_ev("opened", offset=7200), _ev("opened", offset=100)]
        buckets = rollup_events(events, period_seconds=3600, reference=self.REF)
        assert buckets[0].period_start < buckets[1].period_start
