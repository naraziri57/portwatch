"""Command-line entry point for portwatch."""

import argparse
import logging
import sys
from pathlib import Path

from portwatch.alerter import Alerter, stderr_handler, log_handler
from portwatch.watcher import Watcher, DEFAULT_INTERVAL, DEFAULT_SNAPSHOT_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portwatch",
        description="Monitor open ports and alert on unexpected changes.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        metavar="SECONDS",
        help=f"Scan interval in seconds (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT_PATH,
        metavar="FILE",
        help=f"Path to snapshot file (default: {DEFAULT_SNAPSHOT_PATH})",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        metavar="FILE",
        help="Append alerts to this log file instead of stderr",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan, print changes, then exit (useful for cron)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    handler = log_handler(args.log_file) if args.log_file else stderr_handler()
    alerter = Alerter(handlers=[handler])

    watcher = Watcher(
        snapshot_path=args.snapshot,
        interval=args.interval,
        alerter=alerter,
    )

    if args.once:
        events = watcher.run_once()
        return 1 if events else 0

    watcher.start()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
