"""CLI subcommand: enrich — scan ports and display enriched event details."""

from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.alerter import ChangeEvent
from portwatch.enrichment import EnrichedEvent, enrich
from portwatch.scanner import PortEntry, scan_ports
from portwatch.severity import Level


def _scan_or_die(args: argparse.Namespace) -> List[PortEntry]:
    """Run a port scan and exit with code 1 on failure."""
    try:
        return scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _make_fake_events(ports: List[PortEntry]) -> List[ChangeEvent]:
    """Wrap each port as an 'opened' ChangeEvent for enrichment purposes."""
    return [ChangeEvent(kind="opened", entry=p) for p in ports]


def _format_enriched(ev: EnrichedEvent, verbose: bool) -> str:
    """Return a human-readable string for one enriched event."""
    lines = [str(ev)]
    if verbose:
        d = ev.to_dict()
        if d.get("tags"):
            lines.append(f"  tags     : {', '.join(d['tags'])}")
        if d.get("score") is not None:
            lines.append(f"  score    : {d['score']}")
        if d.get("geo"):
            geo = d["geo"]
            lines.append(f"  geo      : {geo.get('country', '?')} / {geo.get('city', '?')}")
        lines.append(f"  severity : {d.get('level', Level.INFO)}")
    return "\n".join(lines)


def cmd_enrich(args: argparse.Namespace) -> int:
    """Scan current ports and display enriched information for each."""
    ports = _scan_or_die(args)

    if not ports:
        print("no open ports found")
        return 0

    events = _make_fake_events(ports)
    enriched: List[EnrichedEvent] = [enrich(ev) for ev in events]

    # Optional: filter by minimum severity level
    if hasattr(args, "min_level") and args.min_level:
        level_order = [Level.INFO, Level.WARNING, Level.CRITICAL]
        try:
            threshold = level_order.index(args.min_level)
        except ValueError:
            print(f"unknown level: {args.min_level}", file=sys.stderr)
            return 1
        enriched = [
            e for e in enriched
            if level_order.index(e.level) >= threshold
        ]

    if not enriched:
        print("no events match the specified severity filter")
        return 0

    verbose = getattr(args, "verbose", False)
    for ev in enriched:
        print(_format_enriched(ev, verbose=verbose))

    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the 'enrich' subcommand on the given subparser group."""
    p = sub.add_parser(
        "enrich",
        help="scan ports and display enriched event details",
    )
    p.add_argument(
        "--min-level",
        choices=[Level.INFO, Level.WARNING, Level.CRITICAL],
        default=None,
        metavar="LEVEL",
        help="only show events at or above this severity (info/warning/critical)",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="show tags, score, geo, and severity details",
    )
    p.set_defaults(func=cmd_enrich)
