"""CLI subcommand: portwatch trends — show flapping / high-frequency ports."""

from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.alerter import ChangeEvent
from portwatch.audit import load_audit  # type: ignore[attr-defined]
from portwatch.trends import TrendTracker


def _build_tracker_from_audit(
    audit_path: str, window: int, threshold: int
) -> TrendTracker:
    """Replay audit log into a fresh TrendTracker."""
    tracker = TrendTracker(window_minutes=window)
    try:
        entries = load_audit(audit_path)
    except FileNotFoundError:
        return tracker

    for entry in entries:
        if entry.kind == "opened":
            tracker.record_open(entry.port, entry.proto)
        elif entry.kind == "closed":
            tracker.record_close(entry.port, entry.proto)
    return tracker


def cmd_trends(args: argparse.Namespace) -> int:
    tracker = _build_tracker_from_audit(
        args.audit_file, args.window, args.threshold
    )

    if args.flapping_only:
        trends = tracker.flapping_ports(threshold=args.threshold)
        label = "Flapping ports"
    else:
        trends = tracker.all_trends()
        label = "All tracked ports"

    if not trends:
        print(f"{label}: none detected.")
        return 0

    print(f"{label} (window={args.window}m, threshold={args.threshold}):")
    for t in sorted(trends, key=lambda x: x.total_events, reverse=True):
        flag = " [FLAPPING]" if t.is_flapping(args.threshold) else ""
        print(
            f"  {t.proto.upper():4s} :{t.port:<6d}"
            f"  opens={t.opens}  closes={t.closes}{flag}"
        )
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("trends", help="show port open/close trends")
    p.add_argument(
        "--audit-file",
        default="portwatch_audit.jsonl",
        help="path to audit log (default: portwatch_audit.jsonl)",
    )
    p.add_argument(
        "--window",
        type=int,
        default=60,
        metavar="MINUTES",
        help="rolling window in minutes (default: 60)",
    )
    p.add_argument(
        "--threshold",
        type=int,
        default=3,
        help="flapping threshold — min opens AND closes (default: 3)",
    )
    p.add_argument(
        "--flapping-only",
        action="store_true",
        help="show only ports that are flapping",
    )
    p.set_defaults(func=cmd_trends)
