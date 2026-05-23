"""CLI sub-command: heartbeat — show or reset heartbeat state."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from portwatch.heartbeat import Heartbeat, HeartbeatConfig

# Module-level singleton so the daemon and CLI share state in-process.
_heartbeat: Heartbeat = Heartbeat(HeartbeatConfig())


def get_heartbeat() -> Heartbeat:
    return _heartbeat


def cmd_heartbeat_status(args: argparse.Namespace) -> int:
    """Print current heartbeat state as JSON or plain text."""
    hb = get_heartbeat()
    state = hb.state.to_dict()
    if getattr(args, "json", False):
        print(json.dumps(state, indent=2))
    else:
        print(f"beats      : {state['beats']}")
        print(f"uptime (s) : {state['uptime_seconds']}")
        last = state["last_beat_at"]
        print(f"last beat  : {'never' if last is None else f'{last:.2f}s ago (monotonic)'}")
    return 0


def cmd_heartbeat_reset(args: argparse.Namespace) -> int:
    """Reset the heartbeat counter and timer."""
    get_heartbeat().reset()
    print("Heartbeat reset.", file=sys.stderr)
    return 0


def cmd_heartbeat_ping(args: argparse.Namespace) -> int:
    """Force an immediate heartbeat beat."""
    get_heartbeat().force_beat()
    beats = get_heartbeat().state.beats
    print(f"Beat forced. Total beats: {beats}", file=sys.stderr)
    return 0


_DISPATCH = {
    "status": cmd_heartbeat_status,
    "reset": cmd_heartbeat_reset,
    "ping": cmd_heartbeat_ping,
}


def _dispatch_heartbeat(args: argparse.Namespace) -> int:
    action = getattr(args, "heartbeat_action", "status")
    handler = _DISPATCH.get(action)
    if handler is None:
        print(f"Unknown heartbeat action: {action}", file=sys.stderr)
        return 1
    return handler(args)


def register_subcommands(subparsers) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("heartbeat", help="heartbeat status and control")
    p.add_argument("--json", action="store_true", help="output as JSON")
    sub = p.add_subparsers(dest="heartbeat_action")

    sub.add_parser("status", help="show heartbeat state")
    sub.add_parser("reset", help="reset heartbeat counter")
    sub.add_parser("ping", help="force an immediate beat")

    p.set_defaults(func=_dispatch_heartbeat)
