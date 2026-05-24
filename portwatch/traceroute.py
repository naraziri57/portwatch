"""Lightweight traceroute-style hop recorder for open ports."""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from typing import List, Optional

from portwatch.scanner import PortEntry


@dataclass
class HopResult:
    ttl: int
    address: Optional[str]
    rtt_ms: Optional[float]
    timed_out: bool = False

    def to_dict(self) -> dict:
        return {
            "ttl": self.ttl,
            "address": self.address,
            "rtt_ms": round(self.rtt_ms, 3) if self.rtt_ms is not None else None,
            "timed_out": self.timed_out,
        }

    def __str__(self) -> str:
        if self.timed_out:
            return f"{self.ttl:>3}  * * *"
        addr = self.address or "?"
        rtt = f"{self.rtt_ms:.1f} ms" if self.rtt_ms is not None else "? ms"
        return f"{self.ttl:>3}  {addr:<20} {rtt}"


@dataclass
class TracerouteResult:
    entry: PortEntry
    hops: List[HopResult] = field(default_factory=list)
    reached: bool = False

    def to_dict(self) -> dict:
        return {
            "port": self.entry.port,
            "proto": self.entry.proto,
            "address": self.entry.address,
            "reached": self.reached,
            "hops": [h.to_dict() for h in self.hops],
        }

    def summary(self) -> str:
        lines = [f"Traceroute to {self.entry.address}:{self.entry.port}/{self.entry.proto}"]
        for hop in self.hops:
            lines.append(str(hop))
        status = "reached" if self.reached else "not reached"
        lines.append(f"Destination {status} in {len(self.hops)} hop(s).")
        return "\n".join(lines)


def _probe_hop(host: str, port: int, ttl: int, timeout: float) -> HopResult:
    start = time.monotonic()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            s.settimeout(timeout)
            s.connect((host, port))
        rtt = (time.monotonic() - start) * 1000
        return HopResult(ttl=ttl, address=host, rtt_ms=rtt)
    except socket.timeout:
        return HopResult(ttl=ttl, address=None, rtt_ms=None, timed_out=True)
    except OSError:
        rtt = (time.monotonic() - start) * 1000
        return HopResult(ttl=ttl, address=host, rtt_ms=rtt)


def run_traceroute(
    entry: PortEntry,
    max_hops: int = 10,
    timeout: float = 1.0,
) -> TracerouteResult:
    if max_hops < 1 or max_hops > 64:
        raise ValueError("max_hops must be between 1 and 64")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    host = entry.address if entry.address not in ("", "0.0.0.0", "::") else "127.0.0.1"
    result = TracerouteResult(entry=entry)

    for ttl in range(1, max_hops + 1):
        hop = _probe_hop(host, entry.port, ttl, timeout)
        result.hops.append(hop)
        if not hop.timed_out:
            result.reached = True
            break

    return result
