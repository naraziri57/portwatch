"""Central registry that wires all subcommands into the top-level parser."""
from __future__ import annotations

import argparse

from portwatch.commands import baseline_cmd, report_cmd, watch_cmd


_MODULES = [
    watch_cmd,
    report_cmd,
    baseline_cmd,
]


def register_all(parser: argparse.ArgumentParser) -> None:
    """Attach every subcommand module to *parser*.

    Each module must expose a ``register_subcommands(subparsers)`` function.
    """
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
    )
    for module in _MODULES:
        module.register_subcommands(subparsers)


def dispatch(args: argparse.Namespace) -> int:
    """Call the handler attached to *args.func* or print help and return 1."""
    if not hasattr(args, "func"):
        # No subcommand given — caller should print help.
        return 1
    return args.func(args)
