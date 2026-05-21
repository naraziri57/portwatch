"""Tests for portwatch.commands.ratelimit_mixin."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.ratelimit_mixin import RateLimitMixin
from portwatch.ratelimit import RateLimiter


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    RateLimitMixin.add_ratelimit_args(p)
    return p


class TestAddRatelimitArgs:
    def test_default_interval(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args([])
        assert args.min_interval == 5.0

    def test_custom_interval(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["--min-interval", "30"])
        assert args.min_interval == 30.0


class TestBuildLimiter:
    def test_returns_rate_limiter(self) -> None:
        args = argparse.Namespace(min_interval=10.0)
        limiter = RateLimitMixin.build_limiter(args)
        assert isinstance(limiter, RateLimiter)
        assert limiter.min_interval == 10.0

    def test_returns_none_when_zero(self) -> None:
        args = argparse.Namespace(min_interval=0)
        assert RateLimitMixin.build_limiter(args) is None

    def test_returns_none_when_negative(self) -> None:
        args = argparse.Namespace(min_interval=-1.0)
        assert RateLimitMixin.build_limiter(args) is None

    def test_returns_none_when_missing(self) -> None:
        args = argparse.Namespace()
        assert RateLimitMixin.build_limiter(args) is None


class TestApplyLimit:
    def test_none_limiter_is_noop(self) -> None:
        # Should not raise
        RateLimitMixin.apply_limit(None)

    def test_calls_wait_when_not_ready(self) -> None:
        limiter = MagicMock(spec=RateLimiter)
        limiter.ready.return_value = False
        limiter.time_until_ready.return_value = 0.1
        RateLimitMixin.apply_limit(limiter)
        limiter.wait.assert_called_once()
        limiter.mark.assert_called_once()

    def test_skips_wait_when_ready(self) -> None:
        limiter = MagicMock(spec=RateLimiter)
        limiter.ready.return_value = True
        RateLimitMixin.apply_limit(limiter)
        limiter.wait.assert_not_called()
        limiter.mark.assert_called_once()
