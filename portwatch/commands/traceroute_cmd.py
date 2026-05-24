"""CLI sub-command: traceroute — probe hops to open ports."""
from __future__ import annotations

import argparse
import sys

from portwatch.scanner import scan_ports
from portwatch.traceroute import run_traceroute


def cmd_traceroute(args: argparse.Namespace) -> int:
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1

    if not ports:
        print("No open ports found.")
        return 0

    tcp_ports = [p for p in ports if p.proto == "tcp"]
    if not tcp_ports:
        print("No TCP ports available for traceroute.")
        return 0

    targets = tcp_ports[: args.limit]
    exit_code = 0

    for entry in targets:
        try:
            result = run_traceroute(
                entry,
                max_hops=args.max_hops,
                timeout=args.timeout,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"traceroute error for port {entry.port}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        print(result.summary())
        print()

        if args.fail_unreachable and not result.reached:
            exit_code = 2

    return exit_code


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("traceroute", help="probe hops to open ports")
    p.add_argument(
        "--max-hops",
        type=int,
        default=10,
        metavar="N",
        help="maximum TTL / hop count (default: 10)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        metavar="SEC",
        help="per-hop timeout in seconds (default: 1.0)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=5,
        metavar="N",
        help="max number of ports to probe (default: 5)",
    )
    p.add_argument(
        "--fail-unreachable",
        action="store_true",
        help="exit 2 if any port was not reached",
    )
    p.set_defaults(func=cmd_traceroute)
