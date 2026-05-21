"""CLI sub-command: portwatch notify — test notification backends."""

from __future__ import annotations

import argparse
import sys
from typing import List

from portwatch.alerter import ChangeEvent
from portwatch.config import load_config
from portwatch.notifier import build_notifiers
from portwatch.scanner import PortEntry, scan_ports


def cmd_notify_test(args: argparse.Namespace) -> int:
    """Send a synthetic test event through all configured notifiers."""
    try:
        cfg = load_config(args.config) if args.config else None
    except Exception as exc:  # noqa: BLE001
        print(f"error loading config: {exc}", file=sys.stderr)
        return 1

    email_cfg = getattr(cfg, "email", None) if cfg else None
    webhook_cfg = getattr(cfg, "webhook", None) if cfg else None

    # Allow CLI overrides
    if args.webhook_url:
        webhook_cfg = {"enabled": True, "url": args.webhook_url}

    notifiers = build_notifiers(
        email_cfg=email_cfg,
        webhook_cfg=webhook_cfg,
    )

    if not notifiers:
        print("no notifiers configured — nothing to test", file=sys.stderr)
        return 1

    test_entry = PortEntry(
        port=0,
        proto="tcp",
        local_addr="127.0.0.1",
        process="portwatch-test",
    )
    test_events: List[ChangeEvent] = [
        ChangeEvent(kind="opened", entry=test_entry)
    ]

    errors = 0
    for notifier in notifiers:
        try:
            notifier.notify(test_events)
            print(f"ok: {type(notifier).__name__}")
        except Exception as exc:  # noqa: BLE001
            print(f"failed: {type(notifier).__name__}: {exc}", file=sys.stderr)
            errors += 1

    return 0 if errors == 0 else 1


def register_subcommands(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Attach the *notify* sub-command tree to *subparsers*."""
    notify_parser = subparsers.add_parser(
        "notify",
        help="manage and test notification backends",
    )
    notify_sub = notify_parser.add_subparsers(dest="notify_action")

    # portwatch notify test
    test_parser = notify_sub.add_parser("test", help="send a test notification")
    test_parser.add_argument(
        "--config", metavar="FILE", default=None, help="path to config file"
    )
    test_parser.add_argument(
        "--webhook-url",
        metavar="URL",
        default=None,
        help="webhook URL to test (overrides config)",
    )
    test_parser.set_defaults(func=cmd_notify_test)

    # Default handler when no sub-action given
    notify_parser.set_defaults(func=lambda a: (notify_parser.print_help(), 0)[1])
