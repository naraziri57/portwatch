"""Snapshot management — save and load port state to/from disk."""

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from portwatch.scanner import PortEntry

DEFAULT_SNAPSHOT_PATH = Path("/var/lib/portwatch/snapshot.json")


def save_snapshot(ports: set[PortEntry], path: Path = DEFAULT_SNAPSHOT_PATH) -> None:
    """Persist current port set to disk as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ports": [
            {
                "proto": p.proto,
                "local_addr": p.local_addr,
                "local_port": p.local_port,
                "pid": p.pid,
                "process": p.process,
            }
            for p in sorted(ports, key=lambda e: (e.proto, e.local_addr, e.local_port))
        ],
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def load_snapshot(path: Path = DEFAULT_SNAPSHOT_PATH) -> Optional[tuple[datetime, set[PortEntry]]]:
    """Load a previously saved snapshot.  Returns (timestamp, ports) or None."""
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    ts = datetime.fromisoformat(raw["timestamp"])
    ports = {
        PortEntry(
            proto=e["proto"],
            local_addr=e["local_addr"],
            local_port=e["local_port"],
            pid=e["pid"],
            process=e["process"],
        )
        for e in raw["ports"]
    }
    return ts, ports


def diff_snapshots(
    old: set[PortEntry], new: set[PortEntry]
) -> tuple[set[PortEntry], set[PortEntry]]:
    """Return (appeared, disappeared) port sets."""
    appeared = new - old
    disappeared = old - new
    return appeared, disappeared
