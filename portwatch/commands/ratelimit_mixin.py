"""Mixin that adds rate-limit support to watch-style commands."""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from portwatch.ratelimit import RateLimiter

logger = logging.getLogger(__name__)


class RateLimitMixin:
    """Attach to a command class to get --min-interval CLI support."""

    @staticmethod
    def add_ratelimit_args(parser: argparse.ArgumentParser) -> None:
        """Register --min-interval argument on *parser*."""
        parser.add_argument(
            "--min-interval",
            type=float,
            default=5.0,
            metavar="SECS",
            help="minimum seconds between scan cycles (default: 5)",
        )

    @staticmethod
    def build_limiter(args: argparse.Namespace) -> Optional[RateLimiter]:
        """Return a RateLimiter from parsed *args*, or None if disabled."""
        interval = getattr(args, "min_interval", None)
        if interval is None or interval <= 0:
            logger.debug("Rate limiting disabled")
            return None
        logger.debug("Rate limiter configured: min_interval=%.2fs", interval)
        return RateLimiter(min_interval=interval)

    @staticmethod
    def apply_limit(limiter: Optional[RateLimiter]) -> None:
        """Block until the limiter allows the next cycle, then mark it."""
        if limiter is None:
            return
        if not limiter.ready():
            wait = limiter.time_until_ready()
            logger.debug("Rate limiter: waiting %.2fs", wait)
            limiter.wait()
        limiter.mark()
