"""Shadow port detection — flag ports that bind only on loopback or link-local
addresses, which may indicate hidden or suspicious services."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Iterable

from portwatch.scanner import PortEntry


_LOOPBACK_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]

_LINK_LOCAL_NETS = [
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_shadow_address(addr: str) -> bool:
    """Return True if *addr* is loopback or link-local (not wildcard)."""
    if addr in ("", "0.0.0.0", "::", "*"):
        return False
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    nets = _LOOPBACK_NETS + _LINK_LOCAL_NETS
    return any(ip in net for net in nets)


@dataclass(frozen=True)
class ShadowPort:
    entry: PortEntry
    reason: str

    def __str__(self) -> str:
        proc = self.entry.process or "unknown"
        return (
            f"[shadow] {self.entry.proto}:{self.entry.port} "
            f"addr={self.entry.address} proc={proc} — {self.reason}"
        )


def detect_shadow_ports(ports: Iterable[PortEntry]) -> list[ShadowPort]:
    """Return a list of ShadowPort entries for any port bound to a
    loopback or link-local address."""
    results: list[ShadowPort] = []
    for entry in ports:
        if not _is_shadow_address(entry.address):
            continue
        ip = ipaddress.ip_address(entry.address)
        if any(ip in net for net in _LOOPBACK_NETS):
            reason = "loopback-only binding"
        else:
            reason = "link-local binding"
        results.append(ShadowPort(entry=entry, reason=reason))
    return results
