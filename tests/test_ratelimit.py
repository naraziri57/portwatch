"""Tests for portwatch.ratelimit."""

from __future__ import annotations

import time
import pytest

from portwatch.ratelimit import RateLimiter


@pytest.fixture
def limiter() -> RateLimiter:
    return RateLimiter(min_interval=1.0)


class TestRateLimiterReady:
    def test_ready_before_first_mark(self, limiter: RateLimiter) -> None:
        assert limiter.ready() is True

    def test_not_ready_immediately_after_mark(self, limiter: RateLimiter) -> None:
        limiter.mark()
        assert limiter.ready() is False

    def test_ready_after_interval_passes(self) -> None:
        rl = RateLimiter(min_interval=0.05)
        rl.mark()
        time.sleep(0.06)
        assert rl.ready() is True


class TestRateLimiterWait:
    def test_wait_returns_quickly_when_ready(self, limiter: RateLimiter) -> None:
        start = time.monotonic()
        limiter.wait()
        assert (time.monotonic() - start) < 0.05

    def test_wait_blocks_until_interval(self) -> None:
        rl = RateLimiter(min_interval=0.1)
        rl.mark()
        start = time.monotonic()
        rl.wait()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08  # allow small timing slack


class TestRateLimiterTimeUntilReady:
    def test_zero_before_first_mark(self, limiter: RateLimiter) -> None:
        assert limiter.time_until_ready() == 0.0

    def test_positive_immediately_after_mark(self, limiter: RateLimiter) -> None:
        limiter.mark()
        assert limiter.time_until_ready() > 0.0

    def test_zero_after_interval_passes(self) -> None:
        rl = RateLimiter(min_interval=0.05)
        rl.mark()
        time.sleep(0.06)
        assert rl.time_until_ready() == 0.0


def test_invalid_interval_raises() -> None:
    with pytest.raises(ValueError, match="positive"):
        RateLimiter(min_interval=0)


def test_negative_interval_raises() -> None:
    with pytest.raises(ValueError):
        RateLimiter(min_interval=-5.0)


def test_mark_updates_last_run() -> None:
    rl = RateLimiter(min_interval=0.5)
    assert rl._last_run is None
    rl.mark()
    assert rl._last_run is not None
