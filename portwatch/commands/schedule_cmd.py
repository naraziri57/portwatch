"""CLI sub-commands for managing scan schedules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import time as dt_time
from typing import List

from portwatch.schedule import ScanSchedule, ScheduleWindow

_DEFAULT_PATH = Path("portwatch_schedule.json")


def _load_schedule(path: Path) -> ScanSchedule:
    if not path.exists():
        return ScanSchedule()
    data = json.loads(path.read_text())
    windows = [ScheduleWindow.from_dict(w) for w in data.get("windows", [])]
    return ScanSchedule(windows=windows, default_active=data.get("default_active", True))


def _save_schedule(schedule: ScanSchedule, path: Path) -> None:
    data = {
        "default_active": schedule.default_active,
        "windows": [w.to_dict() for w in schedule.windows],
    }
    path.write_text(json.dumps(data, indent=2))


def cmd_schedule_add(args: argparse.Namespace) -> int:
    path = Path(args.schedule_file)
    schedule = _load_schedule(path)
    days: List[int] = [int(d) for d in args.days.split(",")] if args.days else list(range(7))
    start = dt_time(*map(int, args.start.split(":")))
    end = dt_time(*map(int, args.end.split(":")))
    window = ScheduleWindow(name=args.name, start=start, end=end, days=days)
    schedule.windows.append(window)
    _save_schedule(schedule, path)
    print(f"Added window '{args.name}' ({args.start}-{args.end})")
    return 0


def cmd_schedule_list(args: argparse.Namespace) -> int:
    schedule = _load_schedule(Path(args.schedule_file))
    if not schedule.windows:
        print("No windows defined (always active).")
        return 0
    for w in schedule.windows:
        day_str = ",".join(str(d) for d in w.days)
        print(f"  {w.name}: {w.start.strftime('%H:%M')}-{w.end.strftime('%H:%M')} days=[{day_str}]")
    return 0


def cmd_schedule_clear(args: argparse.Namespace) -> int:
    path = Path(args.schedule_file)
    _save_schedule(ScanSchedule(), path)
    print("Schedule cleared.")
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("schedule", help="manage scan schedules")
    p.add_argument("--schedule-file", default=str(_DEFAULT_PATH))
    sp = p.add_subparsers(dest="schedule_action")

    add_p = sp.add_parser("add", help="add a time window")
    add_p.add_argument("name")
    add_p.add_argument("--start", required=True, help="HH:MM")
    add_p.add_argument("--end", required=True, help="HH:MM")
    add_p.add_argument("--days", default="", help="comma-separated 0-6 (Mon=0)")

    sp.add_parser("list", help="list windows")
    sp.add_parser("clear", help="remove all windows")


def _dispatch_schedule(args: argparse.Namespace) -> int:
    action = getattr(args, "schedule_action", None)
    if action == "add":
        return cmd_schedule_add(args)
    if action == "list":
        return cmd_schedule_list(args)
    if action == "clear":
        return cmd_schedule_clear(args)
    print("No schedule action specified. Use add / list / clear.")
    return 1
