"""Port scanner module for portwatch.

Responsible for scanning open TCP/UDP ports on the local machine
and returning a snapshot of the current port state.
"""

import socket
import subprocess
import re
from dataclasses import dataclass, field
from typing import Set


@dataclass(frozen=True)
class PortEntry:
    """Represents a single open port entry."""
    protocol: str  # 'tcp' or 'udp'
    port: int
    pid: int | None = None
    process_name: str | None = None

    def __str__(self) -> str:
        proc = f" ({self.process_name}/{self.pid})" if self.process_name else ""
        return f"{self.protocol.upper()}:{self.port}{proc}"


def scan_ports() -> Set[PortEntry]:
    """Scan currently open ports using ss (or netstat as fallback).

    Returns a set of PortEntry objects representing all listening ports.
    """
    entries: Set[PortEntry] = set()

    try:
        result = subprocess.run(
            ["ss", "-tlunpH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.strip().splitlines()
        for line in lines:
            entry = _parse_ss_line(line)
            if entry:
                entries.add(entry)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Fallback: try netstat
        entries = _scan_with_netstat()

    return entries


def _parse_ss_line(line: str) -> PortEntry | None:
    """Parse a single line from `ss -tlunpH` output."""
    parts = line.split()
    if len(parts) < 5:
        return None

    proto = parts[0].lower().rstrip('6')  # normalize tcp6 -> tcp
    local_addr = parts[4]

    # Extract port from address like *:22 or 0.0.0.0:8080 or [::]:443
    port_match = re.search(r':([\d]+)$', local_addr)
    if not port_match:
        return None
    port = int(port_match.group(1))

    pid = None
    process_name = None
    proc_match = re.search(r'pid=(\d+)', line)
    name_match = re.search(r'users:\(\("([^"]+)"', line)
    if proc_match:
        pid = int(proc_match.group(1))
    if name_match:
        process_name = name_match.group(1)

    return PortEntry(protocol=proto, port=port, pid=pid, process_name=process_name)


def _scan_with_netstat() -> Set[PortEntry]:
    """Fallback port scan using netstat."""
    entries: Set[PortEntry] = set()
    try:
        result = subprocess.run(
            ["netstat", "-tlunp"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) < 4 or parts[0] not in ("tcp", "tcp6", "udp", "udp6"):
                continue
            proto = parts[0].rstrip('6')
            port_match = re.search(r':([\d]+)$', parts[3])
            if port_match:
                entries.add(PortEntry(protocol=proto, port=int(port_match.group(1))))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return entries
