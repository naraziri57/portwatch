"""CLI sub-commands for bandwidth tracking."""
from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.bandwidth import BandwidthSample, BandwidthTracker
from portwatch.scanner import scan_ports


def cmd_bandwidth(args: argparse.Namespace) -> int:
    """Record a bandwidth sample for currently open ports and print stats."""
    try:
        ports = scan_ports()
    except Exception as exc:  # pragma: no cover
        print(f"error: scan failed: {exc}", file=sys.stderr)
        return 1

    tracker = BandwidthTracker()

    for entry in ports:
        sample = BandwidthSample(
            port=entry.port,
            proto=entry.proto,
            bytes_in=getattr(args, "bytes_in", 0),
            bytes_out=getattr(args, "bytes_out", 0),
        )
        tracker.record(sample)

    all_stats = tracker.all_stats()
    if not all_stats:
        print("No open ports found.")
        return 0

    print(f"Bandwidth summary ({len(all_stats)} port(s)):")
    for stats in sorted(all_stats, key=lambda s: s.port):
        print(f"  {stats.summary()}")

    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("bandwidth", help="show bandwidth stats for open ports")
    p.add_argument(
        "--bytes-in",
        type=int,
        default=0,
        dest="bytes_in",
        help="simulated inbound bytes for this sample",
    )
    p.add_argument(
        "--bytes-out",
        type=int,
        default=0,
        dest="bytes_out",
        help="simulated outbound bytes for this sample",
    )
    p.set_defaults(func=cmd_bandwidth)
