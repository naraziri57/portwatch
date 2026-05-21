"""CLI subcommand: watch — run the port watcher daemon."""
from __future__ import annotations

import argparse
import logging
import sys

from portwatch.config import Config, load_config
from portwatch.watcher import Watcher

logger = logging.getLogger(__name__)


def cmd_watch(args: argparse.Namespace) -> int:
    """Start the watcher loop using config from *args*."""
    try:
        cfg = load_config(args.config) if args.config else Config()
    except (ValueError, FileNotFoundError) as exc:
        print(f"portwatch: config error: {exc}", file=sys.stderr)
        return 2

    # CLI overrides
    if args.interval is not None:
        try:
            cfg = Config(
                interval=args.interval,
                snapshot_path=cfg.snapshot_path,
                handlers=cfg.handlers,
            )
        except ValueError as exc:
            print(f"portwatch: {exc}", file=sys.stderr)
            return 2

    watcher = Watcher(
        snapshot_path=cfg.snapshot_path,
        interval=cfg.interval,
        handlers=cfg.handlers,
    )

    if args.once:
        events = watcher.run_once()
        return 0 if events is not None else 1

    try:
        watcher.start()
    except KeyboardInterrupt:
        watcher.stop()

    return 0


def register_subcommands(subparsers) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "watch",
        help="Monitor open ports and alert on changes",
    )
    p.add_argument(
        "--config", "-c",
        metavar="FILE",
        default=None,
        help="Path to TOML config file",
    )
    p.add_argument(
        "--interval", "-i",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Override polling interval (seconds)",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan cycle then exit",
    )
    p.set_defaults(func=cmd_watch)
