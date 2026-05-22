"""CLI sub-command: escalation status."""
from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.escalation import EscalationPolicy, EscalationTracker
from portwatch.scanner import scan_ports


def cmd_escalation_status(args: argparse.Namespace) -> int:
    """Print which open ports are currently tracked as escalation candidates."""
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1

    policy = EscalationPolicy(
        escalate_after=args.escalate_after,
        max_escalations=args.max_escalations,
    )
    tracker = EscalationTracker(policy=policy)

    for p in ports:
        tracker.open(p.proto, p.port)

    keys = tracker.open_keys()
    if not keys:
        print("No open ports being tracked.")
    else:
        print(f"Tracking {len(keys)} open port(s):")
        for k in sorted(keys):
            print(f"  {k}")
    return 0


def register_subcommands(subparsers) -> None:  # type: ignore[type-arg]
    p: argparse.ArgumentParser = subparsers.add_parser(
        "escalation",
        help="Escalation tracking commands",
    )
    sub = p.add_subparsers(dest="escalation_cmd")

    status_p = sub.add_parser("status", help="Show currently tracked ports")
    status_p.add_argument(
        "--escalate-after",
        type=float,
        default=300.0,
        metavar="SECS",
        help="Seconds before first escalation (default: 300)",
    )
    status_p.add_argument(
        "--max-escalations",
        type=int,
        default=3,
        metavar="N",
        help="Maximum escalation repeats (default: 3)",
    )
    status_p.set_defaults(func=cmd_escalation_status)
    p.set_defaults(func=_dispatch_escalation)


def _dispatch_escalation(args: argparse.Namespace) -> int:
    if not getattr(args, "escalation_cmd", None):
        print("Usage: portwatch escalation <status>", file=sys.stderr)
        return 1
    return args.func(args)  # type: ignore[no-any-return]
