"""Syslog notifier — sends change events to the local syslog daemon."""

from __future__ import annotations

import logging
import logging.handlers
from dataclasses import dataclass, field
from typing import List

from portwatch.alerter import ChangeEvent

_FACILITY_MAP = {
    "daemon": logging.handlers.SysLogHandler.LOG_DAEMON,
    "user": logging.handlers.SysLogHandler.LOG_USER,
    "local0": logging.handlers.SysLogHandler.LOG_LOCAL0,
    "local1": logging.handlers.SysLogHandler.LOG_LOCAL1,
    "local2": logging.handlers.SysLogHandler.LOG_LOCAL2,
    "local3": logging.handlers.SysLogHandler.LOG_LOCAL3,
    "local4": logging.handlers.SysLogHandler.LOG_LOCAL4,
    "local5": logging.handlers.SysLogHandler.LOG_LOCAL5,
    "local6": logging.handlers.SysLogHandler.LOG_LOCAL6,
    "local7": logging.handlers.SysLogHandler.LOG_LOCAL7,
}


@dataclass
class SyslogNotifier:
    """Sends a summary of change events to syslog."""

    address: str = "/dev/log"
    facility: str = "daemon"
    ident: str = "portwatch"
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        facility_code = _FACILITY_MAP.get(self.facility)
        if facility_code is None:
            raise ValueError(
                f"Unknown syslog facility {self.facility!r}. "
                f"Choose from: {', '.join(_FACILITY_MAP)}"
            )

        # Determine address — could be a host:port tuple or a socket path
        if ":" in self.address and not self.address.startswith("/"):
            host, _, port_str = self.address.rpartition(":")
            address: object = (host, int(port_str))
        else:
            address = self.address

        handler = logging.handlers.SysLogHandler(
            address=address,  # type: ignore[arg-type]
            facility=facility_code,
        )
        handler.ident = f"{self.ident}: "

        self._logger = logging.getLogger(f"portwatch.syslog.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._logger.addHandler(handler)

    def notify(self, events: List[ChangeEvent]) -> None:
        """Log each event as a separate syslog message."""
        if not events:
            return
        for ev in events:
            self._logger.info(str(ev))


def build_syslog_notifier(cfg: dict) -> SyslogNotifier | None:
    """Build a SyslogNotifier from a config dict, or return None if disabled."""
    if not cfg.get("enabled", False):
        return None
    return SyslogNotifier(
        address=cfg.get("address", "/dev/log"),
        facility=cfg.get("facility", "daemon"),
        ident=cfg.get("ident", "portwatch"),
    )
