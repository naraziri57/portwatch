"""Tests for portwatch.packetloss."""
from __future__ import annotations

import pytest

from portwatch.packetloss import LossStats, PacketLossTracker


# ---------------------------------------------------------------------------
# LossStats
# ---------------------------------------------------------------------------

class TestLossStatsValidation:
    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            LossStats(host="127.0.0.1", window=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            LossStats(host="127.0.0.1", window=-1)


class TestLossStatsMetrics:
    def test_empty_loss_rate_is_zero(self):
        s = LossStats(host="h")
        assert s.loss_rate == 0.0

    def test_all_success_zero_loss(self):
        s = LossStats(host="h", window=4)
        for _ in range(4):
            s.record(True)
        assert s.loss_rate == 0.0

    def test_all_failure_full_loss(self):
        s = LossStats(host="h", window=4)
        for _ in range(4):
            s.record(False)
        assert s.loss_rate == 1.0

    def test_half_loss(self):
        s = LossStats(host="h", window=4)
        s.record(True)
        s.record(False)
        s.record(True)
        s.record(False)
        assert s.loss_rate == pytest.approx(0.5)

    def test_window_evicts_old_results(self):
        s = LossStats(host="h", window=2)
        s.record(False)  # evicted after two more
        s.record(True)
        s.record(True)
        assert s.loss_rate == 0.0

    def test_loss_percent_is_scaled(self):
        s = LossStats(host="h", window=10)
        for _ in range(3):
            s.record(False)
        for _ in range(7):
            s.record(True)
        assert s.loss_percent == pytest.approx(30.0)

    def test_total_probes_counts_records(self):
        s = LossStats(host="h", window=10)
        s.record(True)
        s.record(False)
        assert s.total_probes == 2

    def test_to_dict_has_required_keys(self):
        s = LossStats(host="192.168.1.1")
        d = s.to_dict()
        assert "host" in d
        assert "loss_rate" in d
        assert "loss_percent" in d
        assert "total_probes" in d

    def test_str_contains_host(self):
        s = LossStats(host="10.0.0.1")
        assert "10.0.0.1" in str(s)


# ---------------------------------------------------------------------------
# PacketLossTracker
# ---------------------------------------------------------------------------

class TestPacketLossTracker:
    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            PacketLossTracker(window=0)

    def test_unknown_host_returns_none(self):
        t = PacketLossTracker()
        assert t.stats_for("ghost") is None

    def test_record_creates_entry(self):
        t = PacketLossTracker()
        t.record("10.0.0.1", True)
        assert t.stats_for("10.0.0.1") is not None

    def test_all_stats_sorted_by_host(self):
        t = PacketLossTracker()
        t.record("z.host", True)
        t.record("a.host", False)
        hosts = [s.host for s in t.all_stats()]
        assert hosts == sorted(hosts)

    def test_hosts_above_threshold(self):
        t = PacketLossTracker(window=2)
        t.record("good", True)
        t.record("good", True)
        t.record("bad", False)
        t.record("bad", False)
        above = t.hosts_above_threshold(threshold=0.5)
        assert len(above) == 1
        assert above[0].host == "bad"

    def test_no_hosts_above_threshold_returns_empty(self):
        t = PacketLossTracker()
        t.record("ok", True)
        assert t.hosts_above_threshold(threshold=0.0) == []
