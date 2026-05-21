"""CLI subcommand: generate and print a port report."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from portwatch.config import Config, load_config
from portwatch.reporter import print_report
from portwatch.scanner import scan_ports
from portwatch.baseline import load_baseline, baseline_exists
from portwatch.filter import FilterSet


def cmd_report(args: argparse.Namespace, config: Optional[Config] = None) -> int:
    """Scan current ports and print a human-readable report.

    Returns an exit code (0 = ok, 1 = error).
    """
    if config is None:
        try:
            config = load_config(args.config) if args.config else Config()
        except Exception as exc:  # noqa: BLE001
            print(f"portwatch: config error: {exc}", file=sys.stderr)
            return 1

    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"portwatch: scan failed: {exc}", file=sys.stderr)
        return 1

    # Apply filter rules from config when present
    if config.filters:
        fset = FilterSet(config.filters)
        ports = [p for p in ports if not fset.is_ignored(p)]

    baseline = None
    if args.diff_baseline:
        if not baseline_exists(config.baseline_path):
            print(
                "portwatch: no baseline found — run 'portwatch baseline save' first",
                file=sys.stderr,
            )
            return 1
        baseline = load_baseline(config.baseline_path)

    print_report(ports, baseline=baseline)
    return 0


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "report",
        help="Print a snapshot of currently open ports",
    )
    p.add_argument(
        "--diff-baseline",
        action="store_true",
        default=False,
        help="Highlight differences from the saved baseline",
    )
    p.set_defaults(func=cmd_report)
