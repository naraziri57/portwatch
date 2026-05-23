"""CLI sub-command: timeline — view port event history."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from portwatch.timeline import load_timeline, query_range

DEFAULT_PATH = Path("portwatch_timeline.json")


def cmd_timeline(
    args: argparse.Namespace,
    timeline_path: Path = DEFAULT_PATH,
) -> int:
    entries = load_timeline(timeline_path)

    since = None
    until = None
    try:
        if args.since:
            since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
        if args.until:
            until = datetime.fromisoformat(args.until).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        print(f"[timeline] invalid date: {exc}", file=sys.stderr)
        return 1

    entries = query_range(entries, since=since, until=until)

    if args.kind:
        entries = [e for e in entries if e.kind == args.kind]

    if not entries:
        print("No timeline entries found.")
        return 0

    for e in entries:
        proc = e.process or "unknown"
        print(f"{e.timestamp.isoformat()}  {e.kind:8s}  {e.proto}/{e.port}  {proc}")

    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("timeline", help="show port event history")
    p.add_argument("--since", metavar="ISO", help="start of time range (ISO 8601)")
    p.add_argument("--until", metavar="ISO", help="end of time range (ISO 8601)")
    p.add_argument(
        "--kind",
        choices=["opened", "closed"],
        help="filter by event kind",
    )
    p.set_defaults(func=cmd_timeline)
