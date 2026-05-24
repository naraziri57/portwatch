"""CLI sub-command: show port-change velocity from the audit log."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portwatch.audit import load_audit
from portwatch.velocity import VelocityTracker

_DEFAULT_AUDIT = "portwatch_audit.jsonl"
_DEFAULT_WINDOW = 300.0


def cmd_velocity(args: argparse.Namespace) -> int:
    audit_path = Path(args.audit_file)
    if not audit_path.exists():
        print(f"[velocity] audit file not found: {audit_path}", file=sys.stderr)
        return 1

    try:
        entries = load_audit(audit_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[velocity] failed to read audit: {exc}", file=sys.stderr)
        return 1

    tracker = VelocityTracker(window_seconds=args.window)

    for ae in entries:
        from portwatch.audit import AuditEntry
        from portwatch.alerter import ChangeEvent
        event = ChangeEvent(kind=ae.kind, entry=ae.to_port_entry())
        tracker.record_event(event, ts=ae.timestamp)

    threshold = args.threshold
    stats = tracker.hot_ports(threshold) if args.hot_only else tracker.all_stats()

    if not stats:
        print("[velocity] no events recorded.")
        return 0

    if getattr(args, "json", False):
        print(json.dumps(stats, indent=2))
    else:
        print(f"{'PORT':<8} {'PROTO':<6} {'COUNT':>6} {'RATE/s':>10}")
        print("-" * 34)
        for s in sorted(stats, key=lambda x: x["rate_per_second"], reverse=True):
            print(
                f"{s['port']:<8} {s['proto']:<6} {s['event_count']:>6} "
                f"{s['rate_per_second']:>10.4f}"
            )
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("velocity", help="show port-change velocity")
    p.add_argument("--audit-file", default=_DEFAULT_AUDIT)
    p.add_argument(
        "--window",
        type=float,
        default=_DEFAULT_WINDOW,
        help="sliding window in seconds (default: 300)",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="only show ports with rate >= threshold (default: 0)",
    )
    p.add_argument("--hot-only", action="store_true", help="alias for --threshold 0.1")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=cmd_velocity)
