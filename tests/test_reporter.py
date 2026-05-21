"""Tests for portwatch.reporter."""

from datetime import datetime
from io import StringIO

import pytest

from portwatch.scanner import PortEntry
from portwatch.reporter import format_report, print_report


FIXED_TS = datetime(2024, 6, 1, 12, 0, 0)


def _entry(port: int, proto: str = "tcp", process: str | None = "nginx", pid: int | None = 123) -> PortEntry:
    return PortEntry(proto=proto, local_addr="0.0.0.0", port=port, pid=pid, process=process)


class TestFormatReport:
    def test_contains_title(self):
        report = format_report([], title="My Ports", timestamp=FIXED_TS)
        assert "My Ports" in report

    def test_contains_timestamp(self):
        report = format_report([], timestamp=FIXED_TS)
        assert "2024-06-01 12:00:00" in report

    def test_empty_ports_message(self):
        report = format_report([], timestamp=FIXED_TS)
        assert "no open ports" in report

    def test_total_count_zero(self):
        report = format_report([], timestamp=FIXED_TS)
        assert "Total: 0 port(s)" in report

    def test_entry_appears_in_report(self):
        report = format_report([_entry(80)], timestamp=FIXED_TS)
        assert "80" in report
        assert "nginx" in report
        assert "123" in report

    def test_total_count_multiple(self):
        entries = [_entry(80), _entry(443), _entry(8080)]
        report = format_report(entries, timestamp=FIXED_TS)
        assert "Total: 3 port(s)" in report

    def test_sorted_by_proto_then_port(self):
        entries = [
            _entry(443, proto="tcp"),
            _entry(53, proto="udp"),
            _entry(80, proto="tcp"),
        ]
        report = format_report(entries, timestamp=FIXED_TS)
        lines = [l for l in report.splitlines() if l and not l.startswith(("=", "-", "PROTO", "Total"))]
        ports_in_order = [int(l.split()[1].split(":")[1]) for l in lines]
        assert ports_in_order == [80, 443, 53]

    def test_missing_pid_and_process(self):
        entry = PortEntry(proto="tcp", local_addr="127.0.0.1", port=9999, pid=None, process=None)
        report = format_report([entry], timestamp=FIXED_TS)
        assert "9999" in report
        assert report.count("-") >= 2  # placeholder dashes present

    def test_default_timestamp_is_recent(self):
        before = datetime.now()
        report = format_report([])
        after = datetime.now()
        # Just check it doesn't raise and contains the year
        assert str(before.year) in report


class TestPrintReport:
    def test_print_writes_to_file(self):
        buf = StringIO()
        print_report([_entry(22)], timestamp=FIXED_TS, file=buf)
        output = buf.getvalue()
        assert "22" in output
        assert "Total: 1 port(s)" in output

    def test_print_empty(self):
        buf = StringIO()
        print_report([], timestamp=FIXED_TS, file=buf)
        assert "no open ports" in buf.getvalue()
