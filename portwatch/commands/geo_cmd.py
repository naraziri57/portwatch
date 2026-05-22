"""CLI sub-command: portwatch geo  — show GeoIP info for listening addresses."""
from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.geo import GeoInfo, enrich_with_geoip, resolve_hostname
from portwatch.scanner import PortEntry, scan_ports


def _unique_ips(ports: List[PortEntry]) -> List[str]:
    seen: set = set()
    result = []
    for p in ports:
        addr = p.local_address.split(":")[0]
        if addr and addr not in ("0.0.0.0", "::", "127.0.0.1", "::1", "") and addr not in seen:
            seen.add(addr)
            result.append(addr)
    return result


def cmd_geo(args: argparse.Namespace) -> int:
    try:
        ports = scan_ports()
    except Exception as exc:  # pragma: no cover
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1

    ips = _unique_ips(ports)
    if not ips:
        print("No routable listening addresses found.")
        return 0

    db_path: str | None = getattr(args, "db", None)
    resolve: bool = getattr(args, "resolve", False)

    for ip in ips:
        info: GeoInfo = enrich_with_geoip(ip, db_path=db_path)
        line = str(info)
        if resolve:
            hostname = resolve_hostname(ip)
            if hostname:
                line += f"  [{hostname}]"
        print(line)

    return 0


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("geo", help="show GeoIP info for listening addresses")
    p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="path to MaxMind GeoLite2-City.mmdb (optional)",
    )
    p.add_argument(
        "--resolve",
        action="store_true",
        default=False,
        help="reverse-resolve IPs to hostnames",
    )
    p.set_defaults(func=cmd_geo)
