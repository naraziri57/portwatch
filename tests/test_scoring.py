"""Tests for portwatch.scoring."""
import pytest

from portwatch.alerter import ChangeEvent
from portwatch.scanner import PortEntry
from portwatch.severity import Level
from portwatch.scoring import (
    RiskScore,
    aggregate_score,
    score_event,
    score_events,
)


def _entry(port: int = 8080, proto: str = "tcp", process: str = "app") -> PortEntry:
    return PortEntry(port=port, proto=proto, process=process)


def _ev(kind: str = "opened", port: int = 8080) -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port=port))


class TestScoreEvent:
    def test_returns_risk_score_instance(self):
        score = score_event(_ev())
        assert isinstance(score, RiskScore)

    def test_base_reflects_level(self):
        low = score_event(_ev(), level=Level.LOW)
        high = score_event(_ev(), level=Level.HIGH)
        assert low.base < high.base

    def test_sensitive_port_adds_bonus(self):
        normal = score_event(_ev(port=8080))
        sensitive = score_event(_ev(port=22))
        assert sensitive.bonus > normal.bonus
        assert sensitive.bonus == 20

    def test_non_sensitive_port_no_bonus(self):
        score = score_event(_ev(port=9999))
        assert score.bonus == 0

    def test_opened_multiplier_greater_than_closed(self):
        opened = score_event(ChangeEvent(kind="opened", entry=_entry()))
        closed = score_event(ChangeEvent(kind="closed", entry=_entry()))
        assert opened.multiplier > closed.multiplier

    def test_total_is_nonzero(self):
        score = score_event(_ev())
        assert score.total > 0

    def test_total_formula(self):
        score = score_event(_ev(port=22), level=Level.HIGH)
        expected = int((60 + 20) * 1.5)
        assert score.total == expected

    def test_to_dict_keys(self):
        d = score_event(_ev()).to_dict()
        for key in ("port", "proto", "kind", "base", "bonus", "multiplier", "total"):
            assert key in d

    def test_str_contains_port_and_score(self):
        s = str(score_event(_ev(port=8080)))
        assert "8080" in s
        assert "score=" in s


class TestScoreEvents:
    def test_sorted_highest_first(self):
        events = [_ev(port=9999), _ev(port=22)]
        scores = score_events(events)
        assert scores[0].total >= scores[1].total

    def test_empty_list(self):
        assert score_events([]) == []

    def test_length_matches_input(self):
        events = [_ev(), _ev(port=22), _ev(kind="closed")]
        assert len(score_events(events)) == 3


class TestAggregateScore:
    def test_sum_of_totals(self):
        events = [_ev(port=9999), _ev(port=9998)]
        scores = score_events(events)
        expected = min(sum(s.total for s in scores), 1000)
        assert aggregate_score(scores) == expected

    def test_capped_at_1000(self):
        # generate many high-scoring events
        events = [_ev(port=22) for _ in range(20)]
        scores = score_events(events, level=Level.CRITICAL)
        assert aggregate_score(scores) == 1000

    def test_empty_returns_zero(self):
        assert aggregate_score([]) == 0
