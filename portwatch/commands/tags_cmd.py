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
    return TagSet.from_dict(data)


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
        tag_str = ", ".join(sorted(tags)) if tags else "(none)"
        print(f"{entry.proto}:{entry.port}\t{entry.local_addr}\t{entry.process or '-'}\ttags=[{tag_str}]")

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
