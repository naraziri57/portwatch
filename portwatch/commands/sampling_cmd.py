"""CLI sub-commands for port scan sampling."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portwatch.sampling import SampleStore
from portwatch.scanner import scan_ports

_DEFAULT_STORE = Path("portwatch_samples.json")


def cmd_sampling_record(args: argparse.Namespace) -> int:
    """Scan ports and append a sample to the store."""
    try:
        ports = scan_ports()
    except Exception as exc:  # noqa: BLE001
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1

    store = SampleStore(path=Path(args.store), max_samples=args.max_samples)
    sp = store.record(ports)
    print(f"recorded sample: {sp.port_count} ports at {sp.timestamp:.0f}")
    return 0


def cmd_sampling_stats(args: argparse.Namespace) -> int:
    """Print basic statistics from the sample store."""
    store_path = Path(args.store)
    if not store_path.exists():
        print("no sample data found")
        return 0

    store = SampleStore(path=store_path)
    samples = store.all_samples()
    if not samples:
        print("no samples recorded yet")
        return 0

    avg = store.average_port_count()
    latest = store.latest()
    print(f"total samples : {len(samples)}")
    print(f"avg port count: {avg:.1f}")
    print(f"latest count  : {latest.port_count} at {latest.timestamp:.0f}")
    return 0


def register_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("sampling", help="port scan sampling")
    sp = p.add_subparsers(dest="sampling_cmd")

    rec = sp.add_parser("record", help="capture a sample")
    rec.add_argument("--store", default=str(_DEFAULT_STORE))
    rec.add_argument("--max-samples", type=int, default=1440)

    stat = sp.add_parser("stats", help="show sample statistics")
    stat.add_argument("--store", default=str(_DEFAULT_STORE))

    p.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> int:
    if args.sampling_cmd == "record":
        return cmd_sampling_record(args)
    if args.sampling_cmd == "stats":
        return cmd_sampling_stats(args)
    print("specify a sampling sub-command", file=sys.stderr)
    return 1
