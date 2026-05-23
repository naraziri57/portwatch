"""CLI sub-command: resolve and display tags for currently open ports."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from portwatch.scanner import scan_ports, PortEntry
from portwatch.tags import TagRule, TagSet


def _load_tagset(path: str) -> TagSet:
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    return TagSet.from_dict(data)


def _format_entry(entry: PortEntry, tags: set[str]) -> str:
    """Format a single port entry with its resolved tags for display."""
    tag_str = ", ".join(sorted(tags)) if tags else "(none)"
    process = entry.process or "-"
    return f"{entry.proto}:{entry.port}\t{entry.local_addr}\t{process}\ttags=[{tag_str}]"


def cmd_tags(args: argparse.Namespace) -> int:
    """Scan ports and print resolved tags for each entry."""
    try:
        ports: List[PortEntry] = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1

    tagset = TagSet()
    if args.rules_file:
        try:
            tagset = _load_tagset(args.rules_file)
        except Exception as exc:  # noqa: BLE001
            print(f"failed to load rules: {exc}", file=sys.stderr)
            return 1

    if not ports:
        print("no open ports found")
        return 0

    for entry in sorted(ports, key=lambda e: (e.proto, e.port)):
        tags = tagset.resolve(entry)
        print(_format_entry(entry, tags))

    return 0


def register_subcommands(subparsers) -> None:  # type: ignore[type-arg]
    p: argparse.ArgumentParser = subparsers.add_parser(
        "tags",
        help="show tags for open ports",
    )
    p.add_argument(
        "--rules-file",
        metavar="PATH",
        default=None,
        help="JSON file containing tag rules (TagSet format)",
    )
    p.set_defaults(func=cmd_tags)
