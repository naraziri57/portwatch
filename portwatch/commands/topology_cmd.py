"""CLI sub-command: show network topology grouped by address."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from portwatch.scanner import scan_ports
from portwatch.topology import build_topology


def cmd_topology(args: argparse.Namespace) -> int:
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"error: scan failed: {exc}", file=sys.stderr)
        return 1

    topo = build_topology(ports)

    if topo.is_empty():
        print("No open ports found.")
        return 0

    if args.format == "json":
        print(json.dumps(topo.to_dict(), indent=2))
        return 0

    # plain text
    print(f"Topology — {len(topo.nodes)} address(es), {len(ports)} port(s) total\n")
    for addr in topo.all_addresses():
        node = topo.nodes[addr]
        print(f"  {node.summary()}")
        if args.verbose:
            for entry in sorted(node.ports, key=lambda e: e.port):
                proc = entry.process or "(unknown)"
                print(f"      {entry.proto:4s}  {entry.port:5d}  {proc}")
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("topology", help="show open ports grouped by address")
    p.add_argument(
        "--format",
        choices=["plain", "json"],
        default="plain",
        help="output format (default: plain)",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="show per-port details",
    )
    p.set_defaults(func=cmd_topology)
