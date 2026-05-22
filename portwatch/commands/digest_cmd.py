"""CLI sub-command: portwatch digest — print a digest of recent audit events."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.audit import load_audit, AuditEntry
from portwatch.alerter import ChangeEvent
from portwatch.digest import build_digest


def _audit_entry_to_event(entry: AuditEntry) -> ChangeEvent:
    return ChangeEvent(kind=entry.kind, port=entry.port, proto=entry.proto, process=entry.process)


def cmd_digest(args: argparse.Namespace) -> int:
    audit_path = Path(args.audit_file)
    if not audit_path.exists():
        print("No audit log found.", file=sys.stderr)
        return 1

    try:
        entries = load_audit(audit_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to read audit log: {exc}", file=sys.stderr)
        return 1

    limit = args.limit
    if limit and limit > 0:
        entries = entries[-limit:]

    events = [_audit_entry_to_event(e) for e in entries]
    report = build_digest(events)
    print(report.summary())
    return 0


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "digest",
        help="Print a digest summary of recent audit events",
    )
    p.add_argument(
        "--audit-file",
        default="portwatch_audit.jsonl",
        help="Path to the audit log (default: portwatch_audit.jsonl)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only include the N most recent events (0 = all)",
    )
    p.set_defaults(func=cmd_digest)
