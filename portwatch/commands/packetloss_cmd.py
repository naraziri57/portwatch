"""CLI sub-command: packetloss — probe reachability and report loss rates."""
from __future__ import annotations

import argparse
import sys

from portwatch.packetloss import PacketLossTracker
from portwatch.reachability import check_reachability
from portwatch.scanner import scan_ports


def cmd_packetloss(args: argparse.Namespace) -> int:
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"[error] scan failed: {exc}", file=sys.stderr)
        return 1

    tracker = PacketLossTracker(window=args.probes)

    hosts = {p.address for p in ports if p.address not in ("", "0.0.0.0", "::")}
    if not hosts:
        print("No routable addresses found.")
        return 0

    for host in sorted(hosts):
        for _ in range(args.probes):
            # Use the first port for that host as the probe target
            port_entry = next((p for p in ports if p.address == host), None)
            if port_entry is None:
                continue
            result = check_reachability(port_entry)
            tracker.record(host, result.reachable)

    all_stats = tracker.all_stats()
    if not all_stats:
        print("No data collected.")
        return 0

    print(f"{'HOST':<30} {'PROBES':>6} {'LOSS %':>8}")
    print("-" * 48)
    for s in all_stats:
        print(f"{s.host:<30} {s.total_probes:>6} {s.loss_percent:>7.1f}%")

    above = tracker.hosts_above_threshold(args.threshold / 100.0)
    if above and args.fail_on_loss:
        print(
            f"\n[warn] {len(above)} host(s) exceed {args.threshold}% loss threshold.",
            file=sys.stderr,
        )
        return 2

    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("packetloss", help="probe ports and report packet loss rates")
    p.add_argument(
        "--probes",
        type=int,
        default=5,
        metavar="N",
        help="number of probes per host (default: 5)",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        metavar="PCT",
        help="loss%% threshold for warning (default: 10.0)",
    )
    p.add_argument(
        "--fail-on-loss",
        action="store_true",
        default=False,
        help="exit 2 when any host exceeds the threshold",
    )
    p.set_defaults(func=cmd_packetloss)
