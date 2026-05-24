"""CLI sub-command: replay audit events through the alerter pipeline."""
from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.audit import load_audit
from portwatch.replay import ReplayOptions, replay_entries
from portwatch.alerter import Alerter, log_handler, stderr_handler


def cmd_replay(args: argparse.Namespace) -> int:
    try:
        entries = load_audit(args.audit_file)
    except Exception as exc:  # noqa: BLE001
        print(f"error: cannot load audit file: {exc}", file=sys.stderr)
        return 1

    opts = ReplayOptions(
        speed=0,  # instant replay — no real-time delays in CLI
        start_index=args.start or 0,
        end_index=args.end or None,
        filter_kind=args.kind or None,
    )

    handlers = [log_handler]
    if args.stderr:
        handlers.append(stderr_handler)

    alerter = Alerter(handlers=handlers)

    result = replay_entries(entries, alerter.dispatch, opts)

    print(
        f"replayed {result.replayed} event(s), skipped {result.skipped}",
        file=sys.stderr,
    )
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p: argparse.ArgumentParser = sub.add_parser(
        "replay", help="replay audit events through the alert pipeline"
    )
    p.add_argument("audit_file", help="path to audit JSON-lines file")
    p.add_argument("--kind", choices=["opened", "closed"], default=None,
                   help="filter to only this event kind")
    p.add_argument("--start", type=int, default=0, metavar="N",
                   help="skip the first N entries")
    p.add_argument("--end", type=int, default=None, metavar="N",
                   help="stop after entry index N (exclusive)")
    p.add_argument("--stderr", action="store_true",
                   help="also print events to stderr")
    p.set_defaults(func=cmd_replay)
