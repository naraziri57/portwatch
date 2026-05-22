"""CLI sub-command: portwatch metrics — display runtime metrics."""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import Optional

from portwatch.metrics import get_metrics
from portwatch.scanner import scan_ports


def cmd_metrics(args: Namespace) -> int:
    """Print current metrics to stdout.

    Optionally performs a single scan first so the counters are non-trivial
    even on the very first invocation.
    """
    metrics = get_metrics()

    if getattr(args, "scan", False):
        try:
            scan_ports()
            metrics.record_scan()
        except Exception as exc:  # noqa: BLE001
            metrics.record_error()
            print(f"scan error: {exc}", file=sys.stderr)

    snap = metrics.snapshot()

    if getattr(args, "json", False):
        print(json.dumps(snap.to_dict(), indent=2))
    else:
        print(f"scans_total   : {snap.scans_total}")
        print(f"scan_errors   : {snap.scan_errors}")
        print(f"events_total  : {snap.events_total}")
        if snap.events_by_kind:
            for kind, count in sorted(snap.events_by_kind.items()):
                print(f"  {kind:<18}: {count}")
        else:
            print("  (no events recorded)")
        print(f"captured_at   : {snap.captured_at}")

    return 0


def register_subcommands(sub: "_SubParsersAction") -> None:  # type: ignore[name-defined]
    p: ArgumentParser = sub.add_parser(
        "metrics",
        help="show runtime scan/event counters",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="output as JSON",
    )
    p.add_argument(
        "--scan",
        action="store_true",
        default=False,
        help="run a port scan before printing metrics",
    )
    p.set_defaults(func=cmd_metrics)
