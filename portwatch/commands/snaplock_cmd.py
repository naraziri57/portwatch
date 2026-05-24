"""CLI sub-command: snaplock — inspect or clear stale snapshot lock files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.snaplock import is_locked


def cmd_snaplock_status(args: argparse.Namespace) -> int:
    """Print whether the snapshot file is currently locked."""
    path = Path(args.snapshot)
    locked = is_locked(path)
    status = "LOCKED" if locked else "free"
    print(f"Snapshot {path}: {status}")
    return 0


def cmd_snaplock_clear(args: argparse.Namespace) -> int:
    """Remove a stale lock file if it exists."""
    lock_path = Path(str(args.snapshot) + ".lock")
    if not lock_path.exists():
        print(f"No lock file found at {lock_path}")
        return 0
    try:
        lock_path.unlink()
        print(f"Removed stale lock: {lock_path}")
        return 0
    except OSError as exc:
        print(f"Failed to remove lock: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Sub-command wiring
# ---------------------------------------------------------------------------

def _dispatch_snaplock(args: argparse.Namespace) -> int:
    sub = getattr(args, "snaplock_sub", None)
    if sub == "status":
        return cmd_snaplock_status(args)
    if sub == "clear":
        return cmd_snaplock_clear(args)
    print("snaplock: specify a sub-command (status | clear)", file=sys.stderr)
    return 1


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser(
        "snaplock",
        help="Inspect or clear snapshot lock files",
    )
    parser.add_argument(
        "--snapshot",
        default="/var/lib/portwatch/snapshot.json",
        help="Path to the snapshot file (default: %(default)s)",
    )
    sub = parser.add_subparsers(dest="snaplock_sub")

    sub.add_parser("status", help="Show lock status")
    sub.add_parser("clear", help="Remove stale lock file")

    parser.set_defaults(func=_dispatch_snaplock)
