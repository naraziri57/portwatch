"""Tests for portwatch.throttle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from portwatch.throttle import Throttler


@pytest.fixture()
def throttler() -> Throttler:
    return Throttler(cooldown_seconds=60.0)


class TestShouldSend:
    def test_first_alert_always_sent(self, throttler: Throttler) -> None:
        assert throttler.should_send("tcp", 8080, "opened") is True

    def test_duplicate_within_cooldown_suppressed(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 8080, "opened")
        assert throttler.should_send("tcp", 8080, "opened") is False

    def test_different_port_not_suppressed(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 8080, "opened")
        assert throttler.should_send("tcp", 9090, "opened") is True

    def test_different_change_type_not_suppressed(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 8080, "opened")
        assert throttler.should_send("tcp", 8080, "closed") is True

    def test_different_proto_not_suppressed(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 8080, "opened")
        assert throttler.should_send("udp", 8080, "opened") is True

    def test_after_cooldown_expires_sends_again(self, throttler: Throttler) -> None:
        base = 1000.0
        with patch("portwatch.throttle.time.monotonic", return_value=base):
            throttler.should_send("tcp", 22, "opened")

        with patch("portwatch.throttle.time.monotonic", return_value=base + 61.0):
            assert throttler.should_send("tcp", 22, "opened") is True

    def test_within_cooldown_still_suppressed(self, throttler: Throttler) -> None:
        base = 1000.0
        with patch("portwatch.throttle.time.monotonic", return_value=base):
            throttler.should_send("tcp", 22, "opened")

        with patch("portwatch.throttle.time.monotonic", return_value=base + 30.0):
            assert throttler.should_send("tcp", 22, "opened") is False


class TestSuppressedCount:
    def test_zero_before_any_call(self, throttler: Throttler) -> None:
        assert throttler.get_suppressed_count("tcp", 80, "opened") == 0

    def test_zero_after_first_send(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 80, "opened")
        assert throttler.get_suppressed_count("tcp", 80, "opened") == 0

    def test_increments_on_suppression(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 80, "opened")
        throttler.should_send("tcp", 80, "opened")
        throttler.should_send("tcp", 80, "opened")
        assert throttler.get_suppressed_count("tcp", 80, "opened") == 2


class TestClear:
    def test_clear_all(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 80, "opened")
        throttler.should_send("udp", 53, "closed")
        throttler.clear()
        assert throttler.should_send("tcp", 80, "opened") is True
        assert throttler.should_send("udp", 53, "closed") is True

    def test_clear_by_port(self, throttler: Throttler) -> None:
        throttler.should_send("tcp", 80, "opened")
        throttler.should_send("tcp", 443, "opened")
        throttler.clear(port=80)
        assert throttler.should_send("tcp", 80, "opened") is True
        assert throttler.should_send("tcp", 443, "opened") is False
