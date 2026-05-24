"""CLI sub-command: heatmap — build and display a port-event heatmap."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.audit import load_audit_entries
from portwatch.heatmap import Heatmap, load_heatmap, save_heatmap

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _build_from_audit(audit_path: Path) -> Heatmap:
    heatmap = Heatmap()
    if not audit_path.exists():
        return heatmap
    from portwatch.audit import AuditEntry
    from portwatch.alerter import ChangeEvent
    entries = load_audit_entries(audit_path)
    for ae in entries:
        ev = ChangeEvent(
            kind=ae.kind,
            entry=ae.entry,
            timestamp=ae.timestamp,
        )
        heatmap.record_event(ev)
    return heatmap


def cmd_heatmap(args: argparse.Namespace) -> int:
    audit_path = Path(args.audit_file)
    heatmap = _build_from_audit(audit_path)

    if args.save:
        save_heatmap(heatmap, Path(args.save))
        print(f"Heatmap saved to {args.save}")
        return 0

    peak = heatmap.peak_hour()
    if peak is None:
        print("No events recorded — heatmap is empty.")
        return 0

    print(f"Peak activity: {_DAY_NAMES[peak[0]]} {peak[1]:02d}:00")
    print()

    # Simple text grid: days as rows, hours 0-23 as columns
    header = "     " + "".join(f"{h:2d}" for h in range(24))
    print(header)
    for day in range(7):
        row = f"{_DAY_NAMES[day]}  "
        for hour in range(24):
            count = heatmap.get(day, hour)
            row += " ." if count == 0 else f"{count:2d}"
        print(row)
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("heatmap", help="Show port-event activity heatmap")
    p.add_argument(
        "--audit-file",
        default="portwatch_audit.jsonl",
        help="Path to audit log (default: portwatch_audit.jsonl)",
    )
    p.add_argument(
        "--save",
        metavar="FILE",
        default="",
        help="Save heatmap JSON to FILE instead of printing",
    )
    p.set_defaults(func=cmd_heatmap)
