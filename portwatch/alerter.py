"""Alerter — format and emit alerts when port changes are detected."""

import logging
import sys
from dataclasses import dataclass
from typing import Callable

from portwatch.scanner import PortEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChangeEvent:
    kind: str  # "appeared" | "disappeared"
    port: PortEntry

    def __str__(self) -> str:
        verb = "OPENED" if self.kind == "appeared" else "CLOSED"
        return (
            f"[{verb}] {self.port.proto.upper()} "
            f"{self.port.local_addr}:{self.port.local_port}"
            + (f" ({self.port.process}/{self.port.pid})" if self.port.process else "")
        )


AlertHandler = Callable[[ChangeEvent], None]


def log_handler(event: ChangeEvent) -> None:
    """Write the event to the Python logger (WARNING level)."""
    logger.warning(str(event))


def stderr_handler(event: ChangeEvent) -> None:
    """Print the event to stderr — useful for simple setups."""
    print(str(event), file=sys.stderr)


class Alerter:
    """Collects handlers and dispatches ChangeEvents to all of them."""

    def __init__(self, handlers: list[AlertHandler] | None = None) -> None:
        self.handlers: list[AlertHandler] = handlers or [log_handler]

    def add_handler(self, handler: AlertHandler) -> None:
        self.handlers.append(handler)

    def dispatch(self, appeared: set[PortEntry], disappeared: set[PortEntry]) -> int:
        """Fire events for every changed port.  Returns total events emitted."""
        events: list[ChangeEvent] = [
            ChangeEvent(kind="appeared", port=p) for p in sorted(appeared, key=lambda e: e.local_port)
        ] + [
            ChangeEvent(kind="disappeared", port=p) for p in sorted(disappeared, key=lambda e: e.local_port)
        ]
        for event in events:
            for handler in self.handlers:
                try:
                    handler(event)
                except Exception:  # noqa: BLE001
                    logger.exception("Alert handler %s raised an exception", handler)
        return len(events)
