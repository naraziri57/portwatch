"""Formats and outputs port scan summaries as human-readable reports."""

from __future__ import annotations

import sys
from datetime import datetime
from io import StringIO
from typing import Iterable, TextIO

from portwatch.scanner import PortEntry


HEADER = "{proto:<6} {local_addr:<25} {pid:<8} {process}"
ROW = "{proto:<6} {local_addr:<25} {pid:<8} {process}"
SEP = "-" * 60


def _format_entry(entry: PortEntry) -> str:
    return ROW.format(
        proto=entry.proto,
        local_addr=f"{entry.local_addr}:{entry.port}",
        pid=str(entry.pid) if entry.pid is not None else "-",
        process=entry.process or "-",
    )


def format_report(
    ports: Iterable[PortEntry],
    *,
    title: str = "Open Ports",
    timestamp: datetime | None = None,
) -> str:
    """Return a formatted string report for the given port entries."""
    buf = StringIO()
    ts = timestamp or datetime.now()
    buf.write(f"=== {title} — {ts.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    buf.write(
        HEADER.format(
            proto="PROTO",
            local_addr="LOCAL ADDRESS",
            pid="PID",
            process="PROCESS",
        )
        + "\n"
    )
    buf.write(SEP + "\n")

    entries = sorted(ports, key=lambda e: (e.proto, e.port))
    if not entries:
        buf.write("  (no open ports)\n")
    else:
        for entry in entries:
            buf.write(_format_entry(entry) + "\n")

    buf.write(SEP + "\n")
    buf.write(f"Total: {len(entries)} port(s)\n")
    return buf.getvalue()


def print_report(
    ports: Iterable[PortEntry],
    *,
    title: str = "Open Ports",
    timestamp: datetime | None = None,
    file: TextIO | None = None,
) -> None:
    """Print a formatted report to *file* (defaults to stdout)."""
    out = file or sys.stdout
    out.write(format_report(ports, title=title, timestamp=timestamp))
