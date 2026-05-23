"""CLI subcommand for managing and checking the port allowlist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portwatch.allowlist import Allowlist, AllowRule
from portwatch.scanner import scan_ports

_DEFAULT_PATH = Path("allowlist.json")


def _load_allowlist(path: Path) -> Allowlist:
    if not path.exists():
        return Allowlist()
    data = json.loads(path.read_text())
    return Allowlist.from_dict(data)


def _save_allowlist(allowlist: Allowlist, path: Path) -> None:
    path.write_text(json.dumps(allowlist.to_dict(), indent=2))


def cmd_allowlist_add(args: argparse.Namespace) -> int:
    path = Path(args.file)
    allowlist = _load_allowlist(path)
    rule = AllowRule(
        port=args.port,
        proto=args.proto or None,
        process=args.process or None,
    )
    allowlist.rules.append(rule)
    _save_allowlist(allowlist, path)
    print(f"Added rule: {rule.to_dict()}")
    return 0


def cmd_allowlist_check(args: argparse.Namespace) -> int:
    path = Path(args.file)
    allowlist = _load_allowlist(path)
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1
    flagged = [e for e in ports if not allowlist.is_allowed(e)]
    if not flagged:
        print("All open ports are in the allowlist.")
        return 0
    print(f"{len(flagged)} port(s) not in allowlist:")
    for e in flagged:
        print(f"  {e}")
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("allowlist", help="manage port allowlist")
    s = p.add_subparsers(dest="allowlist_action")

    add_p = s.add_parser("add", help="add a rule to the allowlist")
    add_p.add_argument("--port", type=int, required=True)
    add_p.add_argument("--proto", default="")
    add_p.add_argument("--process", default="")
    add_p.add_argument("--file", default=str(_DEFAULT_PATH))

    chk_p = s.add_parser("check", help="check current ports against allowlist")
    chk_p.add_argument("--file", default=str(_DEFAULT_PATH))


def _dispatch_allowlist(args: argparse.Namespace) -> int:
    action = getattr(args, "allowlist_action", None)
    if action == "add":
        return cmd_allowlist_add(args)
    if action == "check":
        return cmd_allowlist_check(args)
    print("No allowlist action specified.", file=sys.stderr)
    return 1
