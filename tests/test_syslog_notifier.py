"""Tests for portwatch.syslog_notifier."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.scanner import PortEntry
from portwatch.syslog_notifier import SyslogNotifier, build_syslog_notifier


def _entry(port: int = 8080, proto: str = "tcp", process: str = "nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, process=process)


def _event(kind: str = "opened") -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry())


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestSyslogNotifierInit:
    def test_valid_facility_succeeds(self):
        with patch("logging.handlers.SysLogHandler"):
            n = SyslogNotifier(facility="daemon")
        assert n.facility == "daemon"

    def test_unknown_facility_raises(self):
        with pytest.raises(ValueError, match="Unknown syslog facility"):
            SyslogNotifier(facility="bogus")

    def test_host_port_address_parsed(self):
        handler_cls = MagicMock()
        handler_cls.return_value = MagicMock(spec=logging.Handler)
        with patch("logging.handlers.SysLogHandler", handler_cls):
            SyslogNotifier(address="localhost:514")
        call_kwargs = handler_cls.call_args
        assert call_kwargs.kwargs["address"] == ("localhost", 514)

    def test_socket_path_address_kept_as_string(self):
        handler_cls = MagicMock()
        handler_cls.return_value = MagicMock(spec=logging.Handler)
        with patch("logging.handlers.SysLogHandler", handler_cls):
            SyslogNotifier(address="/dev/log")
        call_kwargs = handler_cls.call_args
        assert call_kwargs.kwargs["address"] == "/dev/log"


# ---------------------------------------------------------------------------
# notify()
# ---------------------------------------------------------------------------

class TestSyslogNotifierNotify:
    def _make(self) -> SyslogNotifier:
        with patch("logging.handlers.SysLogHandler") as mock_handler_cls:
            mock_handler_cls.return_value = MagicMock(spec=logging.Handler)
            n = SyslogNotifier()
        return n

    def test_no_events_does_not_log(self):
        n = self._make()
        n._logger = MagicMock()
        n.notify([])
        n._logger.info.assert_not_called()

    def test_single_event_logs_once(self):
        n = self._make()
        n._logger = MagicMock()
        n.notify([_event()])
        assert n._logger.info.call_count == 1

    def test_multiple_events_logged_separately(self):
        n = self._make()
        n._logger = MagicMock()
        n.notify([_event("opened"), _event("closed"), _event("opened")])
        assert n._logger.info.call_count == 3

    def test_message_contains_event_str(self):
        n = self._make()
        n._logger = MagicMock()
        ev = _event("opened")
        n.notify([ev])
        logged_msg = n._logger.info.call_args[0][0]
        assert str(ev) in logged_msg


# ---------------------------------------------------------------------------
# build_syslog_notifier()
# ---------------------------------------------------------------------------

class TestBuildSyslogNotifier:
    def test_disabled_returns_none(self):
        assert build_syslog_notifier({"enabled": False}) is None

    def test_missing_enabled_returns_none(self):
        assert build_syslog_notifier({}) is None

    def test_enabled_returns_instance(self):
        with patch("logging.handlers.SysLogHandler") as mock_cls:
            mock_cls.return_value = MagicMock(spec=logging.Handler)
            result = build_syslog_notifier({"enabled": True})
        assert isinstance(result, SyslogNotifier)

    def test_custom_fields_propagated(self):
        with patch("logging.handlers.SysLogHandler") as mock_cls:
            mock_cls.return_value = MagicMock(spec=logging.Handler)
            result = build_syslog_notifier(
                {"enabled": True, "facility": "local3", "ident": "myapp"}
            )
        assert result.facility == "local3"
        assert result.ident == "myapp"
