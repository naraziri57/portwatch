"""CLI sub-command: shadow — detect ports bound to loopback/link-local."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from portwatch.scanner import scan_ports
from portwatch.shadow import detect_shadow_ports


def cmd_shadow(args: argparse.Namespace) -> int:
    """Scan and report any shadow (loopback/link-local) ports."""
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"error: scan failed: {exc}", file=sys.stderr)
        return 1

    shadows = detect_shadow_ports(ports)

    if not shadows:
        print("No shadow ports detected.")
        return 0

    print(f"Found {len(shadows)} shadow port(s):")
    for s in shadows:
        print(f"  {s}")

    if getattr(args, "fail_on_found", False):
        return 2

    return 0


def register_subcommands(
    sub: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    p = sub.add_parser(
        "shadow",
        help="detect ports bound only to loopback or link-local addresses",
    )
    p.add_argument(
        "--fail-on-found",
        action="store_true",
        default=False,
        help="exit with code 2 if any shadow ports are found",
    )
    p.set_defaults(func=cmd_shadow)
