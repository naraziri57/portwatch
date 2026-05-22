"""Integration: tracker + policy working end-to-end."""
import time
import pytest
from portwatch.escalation import EscalationPolicy, EscalationTracker


def _fast_policy(escalate_after: float = 0.05, max_escalations: int = 2) -> EscalationPolicy:
    return EscalationPolicy(escalate_after=escalate_after, max_escalations=max_escalations)


class TestEscalationLifecycle:
    def test_full_lifecycle(self):
        policy = _fast_policy()
        tracker = EscalationTracker(policy=policy)

        tracker.open("tcp", 9000)
        assert not tracker.due("tcp", 9000)  # not yet

        time.sleep(0.06)
        assert tracker.due("tcp", 9000)  # threshold passed

        count = tracker.mark_escalated("tcp", 9000)
        assert count == 1
        assert not tracker.due("tcp", 9000)  # just escalated

        time.sleep(0.06)
        assert tracker.due("tcp", 9000)  # due again
        count = tracker.mark_escalated("tcp", 9000)
        assert count == 2

        time.sleep(0.06)
        assert not tracker.due("tcp", 9000)  # max reached

    def test_close_then_reopen_resets_state(self):
        policy = _fast_policy()
        tracker = EscalationTracker(policy=policy)

        tracker.open("tcp", 9001)
        time.sleep(0.06)
        tracker.mark_escalated("tcp", 9001)
        tracker.close("tcp", 9001)

        # Re-open should reset the counter
        tracker.open("tcp", 9001)
        time.sleep(0.06)
        assert tracker.due("tcp", 9001)
        count = tracker.mark_escalated("tcp", 9001)
        assert count == 1

    def test_multiple_ports_independent(self):
        policy = _fast_policy()
        tracker = EscalationTracker(policy=policy)

        tracker.open("tcp", 80)
        tracker.open("udp", 53)

        time.sleep(0.06)
        assert tracker.due("tcp", 80)
        assert tracker.due("udp", 53)

        tracker.mark_escalated("tcp", 80)
        assert not tracker.due("tcp", 80)
        assert tracker.due("udp", 53)  # unaffected
