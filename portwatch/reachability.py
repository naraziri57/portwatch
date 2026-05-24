"""Reachability checks — attempt TCP connects to open ports to verify they are truly accepting connections."""
from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import List, Optional

from portwatch.scanner import PortEntry

DEFAULT_TIMEOUT = 2.0


@dataclass(frozen=True)
class ReachabilityResult:
    entry: PortEntry
    reachable: bool
    error: Optional[str] = None

    def __str__(self) -> str:
        status = "reachable" if self.reachable else "unreachable"
        base = f"{self.entry.proto}:{self.entry.port} ({self.entry.address}) -> {status}"
        if self.error:
            return f"{base} [{self.error}]"
        return base


def _probe(address: str, port: int, timeout: float) -> Optional[str]:
    """Try to open a TCP connection. Returns None on success, error string on failure."""
    try:
        with socket.create_connection((address, port), timeout=timeout):
            pass
        return None
    except OSError as exc:
        return str(exc)


def _resolve_address(address: str) -> str:
    """Normalise wildcard / any-address bindings to localhost for probing."""
    wildcards = {"", "0.0.0.0", "::", "*"}
    if address in wildcards:
        return "127.0.0.1"
    return address


def check_reachability(
    ports: List[PortEntry],
    timeout: float = DEFAULT_TIMEOUT,
    tcp_only: bool = True,
) -> List[ReachabilityResult]:
    """Probe each port entry and return a list of ReachabilityResult objects.

    Args:
        ports: List of PortEntry objects to probe.
        timeout: Per-connection timeout in seconds.
        tcp_only: When True, skip UDP entries (UDP probing is unreliable).
    """
    results: List[ReachabilityResult] = []
    for entry in ports:
        if tcp_only and entry.proto.lower() != "tcp":
            continue
        address = _resolve_address(entry.address)
        error = _probe(address, entry.port, timeout)
        results.append(
            ReachabilityResult(entry=entry, reachable=error is None, error=error)
        )
    return results


def unreachable_ports(results: List[ReachabilityResult]) -> List[ReachabilityResult]:
    """Filter results to only those that failed the reachability probe."""
    return [r for r in results if not r.reachable]


def reachable_ports(results: List[ReachabilityResult]) -> List[ReachabilityResult]:
    """Filter results to only those that passed the reachability probe."""
    return [r for r in results if r.reachable]


def summary(results: List[ReachabilityResult]) -> str:
    """Return a short human-readable summary of probe results.

    Example: "5 probed, 4 reachable, 1 unreachable"
    """
    total = len(results)
    ok = sum(1 for r in results if r.reachable)
    fail = total - ok
    return f"{total} probed, {ok} reachable, {fail} unreachable"
