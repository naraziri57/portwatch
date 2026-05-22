"""CLI sub-command: portwatch correlation — show correlated event patterns
from the most recent audit log."""

from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.audit import load_audit, AuditEntry
from portwatch.alerter import ChangeEvent
from portwatch.scanner import PortEntry
from portwatch.correlation import correlate_events


def _audit_entry_to_event(entry: AuditEntry) -> ChangeEvent:
    pe = PortEntry(
        port=entry.port,
        proto=entry.proto,
        address=entry.address,
        process=entry.process,
    )
    return ChangeEvent(kind=entry.kind, entry=pe)


def cmd_correlation(args: argparse.Namespace) -> int:
    audit_path = getattr(args, "audit_file", "portwatch_audit.jsonl")
    try:
        entries: List[AuditEntry] = load_audit(audit_path)
    except FileNotFoundError:
        print(f"No audit log found at {audit_path}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to read audit log: {exc}", file=sys.stderr)
        return 1

    if not entries:
        print("No audit entries found.")
        return 0

    limit = getattr(args, "limit", None)
    if limit:
        entries = entries[-limit:]

    events = [_audit_entry_to_event(e) for e in entries]
    groups = correlate_events(events)

    if not groups:
        print("No correlated patterns detected.")
        return 0

    pattern_filter = getattr(args, "pattern", None)

    printed = 0
    for g in groups:
        if pattern_filter and g.pattern != pattern_filter:
            continue
        print(g.summary())
        if getattr(args, "verbose", False):
            for ev in g.events:
                print(f"  {ev}")
        printed += 1

    if printed == 0:
        print(f"No groups matched pattern filter '{pattern_filter}'.")

    return 0


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "correlation",
        help="Show correlated change-event patterns from the audit log",
    )
    p.add_argument(
        "--audit-file",
        default="portwatch_audit.jsonl",
        help="Path to the audit log (default: portwatch_audit.jsonl)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Only consider the last N audit entries",
    )
    p.add_argument(
        "--pattern",
        default=None,
        choices=["restart", "port-swap", "process-change", "unclassified"],
        help="Filter output to a specific correlation pattern",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print individual events within each group",
    )
    p.set_defaults(func=cmd_correlation)
