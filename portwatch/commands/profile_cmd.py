"""CLI sub-commands for port profile management."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.profile import PortProfile, diff_profile, list_profiles, load_profile, save_profile
from portwatch.scanner import scan_ports

_DEFAULT_DIR = Path(".portwatch/profiles")


def _profile_path(directory: Path, name: str) -> Path:
    return directory / f"{name}.json"


def cmd_profile_save(args: argparse.Namespace) -> int:
    try:
        ports = scan_ports()
    except Exception as exc:  # pragma: no cover
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1
    directory = Path(getattr(args, "dir", _DEFAULT_DIR))
    profile = PortProfile(name=args.name, description=getattr(args, "description", ""), ports=ports)
    save_profile(profile, _profile_path(directory, args.name))
    print(f"profile '{args.name}' saved ({len(ports)} ports)")
    return 0


def cmd_profile_check(args: argparse.Namespace) -> int:
    directory = Path(getattr(args, "dir", _DEFAULT_DIR))
    try:
        profile = load_profile(_profile_path(directory, args.name))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        current = scan_ports()
    except Exception as exc:  # pragma: no cover
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1
    delta = diff_profile(profile, current)
    if not delta["added"] and not delta["removed"]:
        print("no changes from profile")
        return 0
    for e in delta["added"]:
        print(f"  + {e.port}/{e.proto}  {e.process or ''}")
    for e in delta["removed"]:
        print(f"  - {e.port}/{e.proto}  {e.process or ''}")
    return 1 if getattr(args, "fail_on_diff", False) else 0


def cmd_profile_list(args: argparse.Namespace) -> int:
    directory = Path(getattr(args, "dir", _DEFAULT_DIR))
    names = list_profiles(directory)
    if not names:
        print("no profiles found")
    for name in names:
        print(name)
    return 0


def _dispatch_profile(args: argparse.Namespace) -> int:
    return {"save": cmd_profile_save, "check": cmd_profile_check, "list": cmd_profile_list}.get(
        args.profile_action, lambda _: 1
    )(args)


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("profile", help="manage port profiles")
    p.add_argument("--dir", default=str(_DEFAULT_DIR), help="profile directory")
    sub = p.add_subparsers(dest="profile_action")

    ps = sub.add_parser("save", help="save current ports as a named profile")
    ps.add_argument("name", help="profile name")
    ps.add_argument("--description", default="", help="optional description")

    pc = sub.add_parser("check", help="compare current ports against a profile")
    pc.add_argument("name", help="profile name")
    pc.add_argument("--fail-on-diff", action="store_true", dest="fail_on_diff")

    sub.add_parser("list", help="list saved profiles")
    p.set_defaults(func=_dispatch_profile)
