"""CLI sub-commands for the audit log: list and clear."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.audit import clear_audit, load_audit

DEFAULT_AUDIT_PATH = Path("/var/lib/portwatch/audit.json")


def cmd_audit_list(args: argparse.Namespace) -> int:
    path = Path(args.audit_file)
    entries = load_audit(path)
    if not entries:
        print("No audit entries found.")
        return 0
    limit = args.limit
    shown = entries[-limit:] if limit else entries
    for e in shown:
        process = e.process or "<unknown>"
        print(f"{e.timestamp}  {e.kind:6s}  {e.proto}/{e.port}  ({process})")
    return 0


def cmd_audit_clear(args: argparse.Namespace) -> int:
    path = Path(args.audit_file)
    clear_audit(path)
    print(f"Audit log cleared: {path}")
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    audit_parser = sub.add_parser("audit", help="Manage the audit log")
    audit_sub = audit_parser.add_subparsers(dest="audit_cmd")
    audit_parser.set_defaults(func=lambda a: (audit_parser.print_help(), 0)[1])

    # list
    list_p = audit_sub.add_parser("list", help="Print audit log entries")
    list_p.add_argument(
        "--audit-file",
        default=str(DEFAULT_AUDIT_PATH),
        help="Path to audit log (default: %(default)s)",
    )
    list_p.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Show last N entries (0 = all, default: %(default)s)",
    )
    list_p.set_defaults(func=cmd_audit_list)

    # clear
    clear_p = audit_sub.add_parser("clear", help="Delete the audit log")
    clear_p.add_argument(
        "--audit-file",
        default=str(DEFAULT_AUDIT_PATH),
        help="Path to audit log (default: %(default)s)",
    )
    clear_p.set_defaults(func=cmd_audit_clear)


def _dispatch_audit(args: argparse.Namespace) -> int:
    if not hasattr(args, "func"):
        print("No audit sub-command specified.", file=sys.stderr)
        return 1
    return args.func(args)
