"""CLI subcommands for managing the port quarantine list."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portwatch.quarantine import QuarantineEntry, load_quarantine, save_quarantine, add_entry, remove_entry


def cmd_quarantine_add(args: argparse.Namespace) -> int:
    """Add a port/proto pair to the quarantine list."""
    path = Path(args.quarantine_file)
    entries = load_quarantine(path) if path.exists() else []
    entry = QuarantineEntry(
        port=args.port,
        proto=args.proto,
        reason=args.reason or "",
        duration_seconds=args.duration,
    )
    updated = add_entry(entries, entry)
    save_quarantine(path, updated)
    print(f"Quarantined {args.proto}:{args.port} (duration={args.duration}s)")
    return 0


def cmd_quarantine_remove(args: argparse.Namespace) -> int:
    """Remove a port/proto pair from the quarantine list."""
    path = Path(args.quarantine_file)
    if not path.exists():
        print("No quarantine file found.", file=sys.stderr)
        return 1
    entries = load_quarantine(path)
    updated = remove_entry(entries, args.port, args.proto)
    save_quarantine(path, updated)
    print(f"Removed {args.proto}:{args.port} from quarantine.")
    return 0


def cmd_quarantine_list(args: argparse.Namespace) -> int:
    """List all active quarantine entries."""
    path = Path(args.quarantine_file)
    if not path.exists():
        print("No quarantine file found.")
        return 0
    entries = load_quarantine(path)
    active = [e for e in entries if not e.is_expired()]
    if not active:
        print("No active quarantine entries.")
        return 0
    for e in active:
        print(f"  {e.proto}:{e.port}  reason={e.reason!r}  expires={e.expires_at}")
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("quarantine", help="manage port quarantine list")
    p.add_argument("--quarantine-file", default="quarantine.json", metavar="FILE")
    qsub = p.add_subparsers(dest="quarantine_action")

    add_p = qsub.add_parser("add", help="quarantine a port")
    add_p.add_argument("port", type=int)
    add_p.add_argument("--proto", default="tcp")
    add_p.add_argument("--reason", default="")
    add_p.add_argument("--duration", type=int, default=3600, metavar="SECONDS")

    rm_p = qsub.add_parser("remove", help="remove a port from quarantine")
    rm_p.add_argument("port", type=int)
    rm_p.add_argument("--proto", default="tcp")

    qsub.add_parser("list", help="list active quarantine entries")


def _dispatch_quarantine(args: argparse.Namespace) -> int:
    action = getattr(args, "quarantine_action", None)
    if action == "add":
        return cmd_quarantine_add(args)
    if action == "remove":
        return cmd_quarantine_remove(args)
    if action == "list":
        return cmd_quarantine_list(args)
    print("No quarantine action specified. Use add/remove/list.", file=sys.stderr)
    return 1
