"""Tests for portwatch.cooldown."""

from datetime import datetime, timedelta

import pytest

from portwatch.cooldown import CooldownPolicy, CooldownTracker


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------

class TestCooldownPolicyValidation:
    def test_defaults(self):
        p = CooldownPolicy()
        assert p.quiet_period == 300
        assert p.max_suppressions == 10

    def test_zero_quiet_period_raises(self):
        with pytest.raises(ValueError, match="quiet_period"):
            CooldownPolicy(quiet_period=0)

    def test_negative_quiet_period_raises(self):
        with pytest.raises(ValueError):
            CooldownPolicy(quiet_period=-1)

    def test_zero_max_suppressions_raises(self):
        with pytest.raises(ValueError, match="max_suppressions"):
            CooldownPolicy(max_suppressions=0)


# ---------------------------------------------------------------------------
# Tracker behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracker():
    return CooldownTracker(policy=CooldownPolicy(quiet_period=60, max_suppressions=3))


T0 = datetime(2024, 1, 1, 12, 0, 0)


class TestCooldownTracker:
    def test_no_state_not_suppressed(self, tracker):
        assert tracker.is_suppressed(8080, "tcp", now=T0) is False

    def test_suppressed_within_quiet_period(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        soon = T0 + timedelta(seconds=30)
        assert tracker.is_suppressed(8080, "tcp", now=soon) is True

    def test_not_suppressed_after_quiet_period(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        later = T0 + timedelta(seconds=61)
        assert tracker.is_suppressed(8080, "tcp", now=later) is False

    def test_different_port_not_suppressed(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        soon = T0 + timedelta(seconds=10)
        assert tracker.is_suppressed(9090, "tcp", now=soon) is False

    def test_different_proto_not_suppressed(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        soon = T0 + timedelta(seconds=10)
        assert tracker.is_suppressed(8080, "udp", now=soon) is False

    def test_force_realert_after_max_suppressions(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        for _ in range(3):  # max_suppressions == 3
            tracker.record_suppression(8080, "tcp")
        soon = T0 + timedelta(seconds=10)
        assert tracker.is_suppressed(8080, "tcp", now=soon) is False

    def test_suppression_count_increments(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        tracker.record_suppression(8080, "tcp")
        tracker.record_suppression(8080, "tcp")
        assert tracker.suppression_count(8080, "tcp") == 2

    def test_suppression_count_unknown_port_is_zero(self, tracker):
        assert tracker.suppression_count(1234, "tcp") == 0

    def test_reset_clears_entry(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        tracker.reset(8080, "tcp")
        soon = T0 + timedelta(seconds=5)
        assert tracker.is_suppressed(8080, "tcp", now=soon) is False

    def test_reset_all_clears_everything(self, tracker):
        tracker.record_alert(8080, "tcp", now=T0)
        tracker.record_alert(9090, "udp", now=T0)
        tracker.reset_all()
        soon = T0 + timedelta(seconds=5)
        assert tracker.is_suppressed(8080, "tcp", now=soon) is False
        assert tracker.is_suppressed(9090, "udp", now=soon) is False

    def test_proto_case_insensitive(self, tracker):
        tracker.record_alert(443, "TCP", now=T0)
        soon = T0 + timedelta(seconds=5)
        assert tracker.is_suppressed(443, "tcp", now=soon) is True
