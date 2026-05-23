"""CLI sub-command: portwatch diff — compare two snapshot files."""

from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.snapshot import load_snapshot
from portwatch.snapshot_diff import compute_diff
from portwatch.severity import SeverityRule


def cmd_diff(args: argparse.Namespace) -> int:
    """Load two snapshot files and print a human-readable diff."""
    try:
        before = load_snapshot(args.before)
    except Exception as exc:  # noqa: BLE001
        print(f"error: cannot load 'before' snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        after = load_snapshot(args.after)
    except Exception as exc:  # noqa: BLE001
        print(f"error: cannot load 'after' snapshot: {exc}", file=sys.stderr)
        return 1

    rules: List[SeverityRule] = []
    diff = compute_diff(frozenset(before), frozenset(after), severity_rules=rules)

    if diff.is_empty:
        print("No changes between snapshots.")
        return 0

    print(f"Opened ports  : {len(diff.opened)}")
    print(f"Closed ports  : {len(diff.closed)}")
    print()
    for d in diff.opened:
        print(str(d))
    for d in diff.closed:
        print(str(d))

    if args.fail_on_change:
        return 1
    return 0


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "diff",
        help="Compare two snapshot files and report changes.",
    )
    p.add_argument("before", help="Path to the older snapshot JSON file.")
    p.add_argument("after", help="Path to the newer snapshot JSON file.")
    p.add_argument(
        "--fail-on-change",
        action="store_true",
        default=False,
        help="Exit with code 1 if any changes are found (useful in CI).",
    )
    p.set_defaults(func=cmd_diff)
