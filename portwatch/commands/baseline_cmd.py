"""CLI sub-command handlers for baseline management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.baseline import (
    DEFAULT_BASELINE_PATH,
    baseline_exists,
    diff_from_baseline,
    save_baseline,
)
from portwatch.reporter import print_report
from portwatch.scanner import scan_ports


def cmd_baseline_save(args: argparse.Namespace) -> int:
    """Scan current ports and save them as the new baseline."""
    path = Path(args.baseline) if args.baseline else DEFAULT_BASELINE_PATH
    ports = scan_ports()
    save_baseline(ports, path)
    print(f"Baseline saved to {path} ({len(ports)} entries).", file=sys.stderr)
    return 0


def cmd_baseline_check(args: argparse.Namespace) -> int:
    """Compare current ports against the stored baseline and report differences."""
    path = Path(args.baseline) if args.baseline else DEFAULT_BASELINE_PATH
    if not baseline_exists(path):
        print(f"No baseline found at {path}. Run 'portwatch baseline save' first.", file=sys.stderr)
        return 2

    current = scan_ports()
    new_ports, removed_ports = diff_from_baseline(current, path)

    if not new_ports and not removed_ports:
        print("No changes from baseline.", file=sys.stderr)
        return 0

    if new_ports:
        print_report(new_ports, title="New ports (not in baseline)")
    if removed_ports:
        print_report(removed_ports, title="Removed ports (were in baseline)")

    return 1


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Attach baseline sub-commands to an existing subparsers group."""
    baseline_parser = subparsers.add_parser("baseline", help="Manage the trusted-port baseline")
    baseline_parser.add_argument("--baseline", metavar="FILE", help="Override baseline file path")
    sub = baseline_parser.add_subparsers(dest="baseline_action", required=True)

    sub.add_parser("save", help="Capture current ports as the new baseline")
    sub.add_parser("check", help="Compare current ports against the baseline")

    baseline_parser.set_defaults(_dispatch=_dispatch_baseline)


def _dispatch_baseline(args: argparse.Namespace) -> int:
    if args.baseline_action == "save":
        return cmd_baseline_save(args)
    if args.baseline_action == "check":
        return cmd_baseline_check(args)
    return 1
