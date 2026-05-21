"""Alerter wrapper that applies throttling before dispatching change events."""

from __future__ import annotations

import logging
from typing import List, Optional

from portwatch.alerter import Alerter, ChangeEvent
from portwatch.throttle import Throttler

logger = logging.getLogger(__name__)


class ThrottleAwareAlerter:
    """Wraps an Alerter and skips events that are within the throttle window."""

    def __init__(
        self,
        alerter: Alerter,
        cooldown_seconds: float = 300.0,
        throttler: Optional[Throttler] = None,
    ) -> None:
        self.alerter = alerter
        self.throttler = throttler or Throttler(cooldown_seconds=cooldown_seconds)

    def dispatch(self, events: List[ChangeEvent]) -> None:
        """Filter throttled events, then forward the rest to the wrapped alerter."""
        allowed: List[ChangeEvent] = []
        suppressed: List[ChangeEvent] = []

        for event in events:
            proto = event.entry.proto if event.entry else "unknown"
            port = event.entry.port if event.entry else 0
            change_type = event.change_type

            if self.throttler.should_send(proto, port, change_type):
                allowed.append(event)
            else:
                suppressed.append(event)
                count = self.throttler.get_suppressed_count(proto, port, change_type)
                logger.debug(
                    "Throttled %s event for %s:%d (suppressed %d times)",
                    change_type,
                    proto,
                    port,
                    count,
                )

        if suppressed:
            logger.info(
                "%d event(s) suppressed by throttle, %d will be dispatched.",
                len(suppressed),
                len(allowed),
            )

        if allowed:
            self.alerter.dispatch(allowed)

    def reset_throttle(self) -> None:
        """Clear all throttle state (useful for testing or manual resets)."""
        self.throttler.clear()
