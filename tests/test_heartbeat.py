"""Tests for portwatch.heartbeat."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from portwatch.heartbeat import Heartbeat, HeartbeatConfig, HeartbeatState


# ---------------------------------------------------------------------------
# HeartbeatConfig validation
# ---------------------------------------------------------------------------

class TestHeartbeatConfigValidation:
    def test_default_interval(self):
        cfg = HeartbeatConfig()
        assert cfg.interval == 60.0

    def test_zero_interval_raises(self):
        with pytest.raises(ValueError, match="interval"):
            HeartbeatConfig(interval=0)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError):
            HeartbeatConfig(interval=-5)

    def test_custom_interval_accepted(self):
        cfg = HeartbeatConfig(interval=30.0)
        assert cfg.interval == 30.0


# ---------------------------------------------------------------------------
# HeartbeatState
# ---------------------------------------------------------------------------

class TestHeartbeatState:
    def test_initial_beats_zero(self):
        s = HeartbeatState()
        assert s.beats == 0

    def test_record_beat_increments(self):
        s = HeartbeatState()
        s.record_beat()
        assert s.beats == 1

    def test_last_beat_at_set_after_record(self):
        s = HeartbeatState()
        assert s.last_beat_at is None
        s.record_beat()
        assert s.last_beat_at is not None

    def test_to_dict_keys(self):
        s = HeartbeatState()
        d = s.to_dict()
        assert "beats" in d
        assert "uptime_seconds" in d
        assert "last_beat_at" in d

    def test_uptime_is_non_negative(self):
        s = HeartbeatState()
        assert s.uptime_seconds >= 0


# ---------------------------------------------------------------------------
# Heartbeat.tick
# ---------------------------------------------------------------------------

class TestHeartbeatTick:
    def _make(self, interval=10.0, callback=None):
        cfg = HeartbeatConfig(interval=interval, on_beat=callback)
        return Heartbeat(cfg)

    def test_no_beat_before_interval(self):
        hb = self._make(interval=100.0)
        assert hb.tick() is False

    def test_beat_fires_after_interval(self):
        hb = self._make(interval=0.01)
        time.sleep(0.02)
        assert hb.tick() is True

    def test_beat_increments_count(self):
        hb = self._make(interval=0.01)
        time.sleep(0.02)
        hb.tick()
        assert hb.state.beats == 1

    def test_callback_called_on_beat(self):
        calls = []
        hb = self._make(interval=0.01, callback=lambda s: calls.append(s))
        time.sleep(0.02)
        hb.tick()
        assert len(calls) == 1
        assert isinstance(calls[0], HeartbeatState)

    def test_no_callback_when_no_beat(self):
        calls = []
        hb = self._make(interval=100.0, callback=lambda s: calls.append(s))
        hb.tick()
        assert calls == []

    def test_force_beat_fires_immediately(self):
        hb = self._make(interval=100.0)
        hb.force_beat()
        assert hb.state.beats == 1

    def test_reset_clears_state(self):
        hb = self._make(interval=0.01)
        time.sleep(0.02)
        hb.tick()
        hb.reset()
        assert hb.state.beats == 0
        assert hb.state.last_beat_at is None
