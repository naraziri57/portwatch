"""CLI sub-commands for checkpoint management."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from portwatch.checkpoint import list_checkpoints, load_checkpoint, save_checkpoint
from portwatch.scanner import scan_ports

_DEFAULT_DIR = Path(".portwatch/checkpoints")


def _checkpoint_path(directory: Path, label: str) -> Path:
    slug = label.replace(" ", "_") if label else str(int(time.time()))
    return directory / f"checkpoint_{slug}.json"


def cmd_checkpoint_save(args) -> int:
    directory = Path(getattr(args, "directory", _DEFAULT_DIR))
    label = getattr(args, "label", "")
    try:
        ports = scan_ports()
    except Exception as exc:  # pragma: no cover
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1
    path = _checkpoint_path(directory, label)
    cp = save_checkpoint(path, ports, label=label)
    print(f"checkpoint saved: {path} ({len(cp.ports)} ports, label={cp.label!r})")
    return 0


def cmd_checkpoint_list(args) -> int:
    directory = Path(getattr(args, "directory", _DEFAULT_DIR))
    checkpoints = list_checkpoints(directory)
    if not checkpoints:
        print("no checkpoints found")
        return 0
    for cp in checkpoints:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cp.timestamp))
        label = f" [{cp.label}]" if cp.label else ""
        print(f"{ts}{label}  {len(cp.ports)} ports")
    return 0


def cmd_checkpoint_diff(args) -> int:
    path_a = Path(args.checkpoint_a)
    path_b = Path(args.checkpoint_b)
    cp_a = load_checkpoint(path_a)
    cp_b = load_checkpoint(path_b)
    if cp_a is None:
        print(f"not found: {path_a}", file=sys.stderr)
        return 1
    if cp_b is None:
        print(f"not found: {path_b}", file=sys.stderr)
        return 1
    set_a = {(e.port, e.proto) for e in cp_a.ports}
    set_b = {(e.port, e.proto) for e in cp_b.ports}
    added = set_b - set_a
    removed = set_a - set_b
    if not added and not removed:
        print("no differences")
        return 0
    for port, proto in sorted(added):
        print(f"+ {proto}/{port}")
    for port, proto in sorted(removed):
        print(f"- {proto}/{port}")
    return 0


def _dispatch_checkpoint(args) -> int:
    return {
        "save": cmd_checkpoint_save,
        "list": cmd_checkpoint_list,
        "diff": cmd_checkpoint_diff,
    }[args.checkpoint_subcmd](args)


def register_subcommands(subparsers) -> None:
    p = subparsers.add_parser("checkpoint", help="manage port checkpoints")
    sub = p.add_subparsers(dest="checkpoint_subcmd", required=True)

    ps = sub.add_parser("save", help="capture current ports as a checkpoint")
    ps.add_argument("--label", default="", help="human-readable label")
    ps.add_argument("--directory", default=str(_DEFAULT_DIR))

    pl = sub.add_parser("list", help="list saved checkpoints")
    pl.add_argument("--directory", default=str(_DEFAULT_DIR))

    pd = sub.add_parser("diff", help="diff two checkpoint files")
    pd.add_argument("checkpoint_a")
    pd.add_argument("checkpoint_b")

    p.set_defaults(func=_dispatch_checkpoint)
