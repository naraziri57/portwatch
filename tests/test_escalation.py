"""Tests for portwatch.escalation."""
import time
import pytest
from portwatch.escalation import EscalationPolicy, EscalationTracker


# ---------------------------------------------------------------------------
# EscalationPolicy validation
# ---------------------------------------------------------------------------

class TestEscalationPolicyValidation:
    def test_defaults(self):
        p = EscalationPolicy()
        assert p.escalate_after == 300.0
        assert p.max_escalations == 3

    def test_zero_escalate_after_raises(self):
        with pytest.raises(ValueError):
            EscalationPolicy(escalate_after=0)

    def test_negative_escalate_after_raises(self):
        with pytest.raises(ValueError):
            EscalationPolicy(escalate_after=-1)

    def test_zero_max_escalations_raises(self):
        with pytest.raises(ValueError):
            EscalationPolicy(max_escalations=0)


# ---------------------------------------------------------------------------
# EscalationTracker behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracker():
    return EscalationTracker(policy=EscalationPolicy(escalate_after=1.0, max_escalations=2))


def test_not_due_immediately_after_open(tracker):
    tracker.open("tcp", 8080)
    assert tracker.due("tcp", 8080) is False


def test_due_after_threshold(tracker):
    tracker.open("tcp", 8080)
    # Fake the timestamp to be in the past
    tracker._state["tcp:8080"].last_escalated -= 2.0
    assert tracker.due("tcp", 8080) is True


def test_not_due_for_unknown_key(tracker):
    assert tracker.due("tcp", 9999) is False


def test_mark_escalated_increments_count(tracker):
    tracker.open("tcp", 8080)
    tracker._state["tcp:8080"].last_escalated -= 2.0
    count = tracker.mark_escalated("tcp", 8080)
    assert count == 1


def test_stops_after_max_escalations(tracker):
    tracker.open("tcp", 8080)
    for _ in range(2):
        tracker._state["tcp:8080"].last_escalated -= 2.0
        tracker.mark_escalated("tcp", 8080)
    tracker._state["tcp:8080"].last_escalated -= 2.0
    assert tracker.due("tcp", 8080) is False


def test_close_removes_entry(tracker):
    tracker.open("tcp", 8080)
    tracker.close("tcp", 8080)
    assert tracker.due("tcp", 8080) is False
    assert "tcp:8080" not in tracker.open_keys()


def test_mark_escalated_unknown_raises(tracker):
    with pytest.raises(KeyError):
        tracker.mark_escalated("tcp", 1234)


def test_open_keys_returns_all(tracker):
    tracker.open("tcp", 80)
    tracker.open("udp", 53)
    assert set(tracker.open_keys()) == {"tcp:80", "udp:53"}
