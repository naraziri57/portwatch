"""CLI subcommand: latency — probe ports and report round-trip times."""
from __future__ import annotations

import argparse
import socket
import time
from typing import List

from portwatch.latency import LatencyTracker
from portwatch.scanner import scan_ports, PortEntry


def _probe_port(entry: PortEntry, timeout: float) -> float:
    """Attempt a TCP connect and return latency in ms, or -1 on failure."""
    addr = entry.address if entry.address not in ("0.0.0.0", "::", "*") else "127.0.0.1"
    try:
        start = time.perf_counter()
        with socket.create_connection((addr, entry.port), timeout=timeout):
            pass
        return (time.perf_counter() - start) * 1000.0
    except OSError:
        return -1.0


def cmd_latency(args: argparse.Namespace) -> int:
    try:
        ports: List[PortEntry] = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", flush=True)
        return 1

    tracker = LatencyTracker()
    for entry in ports:
        if entry.proto != "tcp":
            continue
        for _ in range(args.samples):
            ms = _probe_port(entry, timeout=args.timeout)
            if ms >= 0:
                tracker.record(entry.port, entry.proto, ms)

    all_stats = tracker.all_stats()
    if not all_stats:
        print("no tcp ports reachable for latency measurement")
        return 0

    print(f"{'PORT':<8} {'PROTO':<6} {'SAMPLES':<9} {'MEAN ms':<10} {'MIN ms':<10} {'MAX ms':<10} {'STDEV ms'}")
    for s in sorted(all_stats, key=lambda x: x.port):
        mean = f"{s.mean_ms:.2f}" if s.mean_ms is not None else "n/a"
        mn   = f"{s.min_ms:.2f}"  if s.min_ms  is not None else "n/a"
        mx   = f"{s.max_ms:.2f}"  if s.max_ms  is not None else "n/a"
        sd   = f"{s.stdev_ms:.2f}" if s.stdev_ms is not None else "n/a"
        print(f"{s.port:<8} {s.proto:<6} {s.sample_count:<9} {mean:<10} {mn:<10} {mx:<10} {sd}")

    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("latency", help="probe open TCP ports and report latency")
    p.add_argument("--samples", type=int, default=3, help="probes per port (default: 3)")
    p.add_argument("--timeout", type=float, default=1.0, help="connect timeout in seconds (default: 1.0)")
    p.set_defaults(func=cmd_latency)
