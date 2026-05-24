"""CLI sub-commands for inspecting and managing the circuit breaker state."""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace

from portwatch.circuit_breaker import CircuitBreaker, BreakerState

# Module-level singleton so the watcher and CLI share the same instance.
_breaker: CircuitBreaker = CircuitBreaker()


def get_breaker() -> CircuitBreaker:
    return _breaker


def cmd_circuit_breaker_status(args: Namespace) -> int:
    breaker = get_breaker()
    data = breaker.to_dict()
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        state = data["state"]
        failures = data["failures"]
        threshold = data["failure_threshold"]
        print(f"Circuit breaker: {state}")
        print(f"Failures: {failures}/{threshold}")
        if state == BreakerState.OPEN.value and data["opened_at"] is not None:
            print(f"Recovery timeout: {data['recovery_timeout']}s")
    return 0


def cmd_circuit_breaker_reset(args: Namespace) -> int:
    get_breaker().reset()
    print("Circuit breaker reset to CLOSED.")
    return 0


def _dispatch(args: Namespace) -> int:
    sub = getattr(args, "circuit_sub", None)
    if sub == "status":
        return cmd_circuit_breaker_status(args)
    if sub == "reset":
        return cmd_circuit_breaker_reset(args)
    print("No sub-command given. Use 'status' or 'reset'.", file=sys.stderr)
    return 1


def register_subcommands(sub_parsers) -> None:
    p: ArgumentParser = sub_parsers.add_parser(
        "circuit-breaker", help="Inspect or reset the circuit breaker"
    )
    subs = p.add_subparsers(dest="circuit_sub")

    status_p = subs.add_parser("status", help="Show current breaker state")
    status_p.add_argument("--json", action="store_true", help="Output as JSON")

    subs.add_parser("reset", help="Manually reset the breaker to CLOSED")

    p.set_defaults(func=_dispatch)
