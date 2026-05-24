"""CLI subcommand: portwatch drift — detect port drift from a saved baseline."""

from __future__ import annotations

import argparse
import json
import sys

from portwatch.baseline import baseline_exists, load_baseline
from portwatch.drift import detect_drift
from portwatch.scanner import scan_ports


def cmd_drift(args: argparse.Namespace) -> int:
    if not baseline_exists(args.baseline):
        print(f"error: baseline not found: {args.baseline}", file=sys.stderr)
        return 1

    try:
        current = set(scan_ports())
    except Exception as exc:  # noqa: BLE001
        print(f"error: scan failed: {exc}", file=sys.stderr)
        return 1

    reference = set(load_baseline(args.baseline))
    result = detect_drift(reference, current)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary())
        if not result.is_clean:
            if result.added:
                print("  Opened ports:")
                for e in sorted(result.added, key=lambda e: e.port):
                    print(f"    {e}")
            if result.removed:
                print("  Closed ports:")
                for e in sorted(result.removed, key=lambda e: e.port):
                    print(f"    {e}")

    if not result.is_clean and args.fail_on_drift:
        return 2
    return 0


def register_subcommands(sub: argparse.Action) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("drift", help="detect port drift from a saved baseline")
    p.add_argument(
        "--baseline",
        default=".portwatch_baseline.json",
        help="path to baseline file (default: .portwatch_baseline.json)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="output results as JSON",
    )
    p.add_argument(
        "--fail-on-drift",
        action="store_true",
        default=False,
        help="exit with code 2 when drift is detected",
    )
    p.set_defaults(func=cmd_drift)
