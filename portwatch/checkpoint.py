"""Periodic checkpoint management for portwatch.

A checkpoint captures a timestamped snapshot of open ports so that
long-running watch sessions can be resumed or compared against a
known-good moment in time.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from portwatch.scanner import PortEntry


@dataclass
class Checkpoint:
    timestamp: float
    ports: List[PortEntry]
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "label": self.label,
            "ports": [
                {
                    "port": e.port,
                    "proto": e.proto,
                    "address": e.address,
                    "process": e.process,
                }
                for e in self.ports
            ],
        }

    @staticmethod
    def from_dict(data: dict) -> "Checkpoint":
        ports = [
            PortEntry(
                port=p["port"],
                proto=p["proto"],
                address=p["address"],
                process=p.get("process"),
            )
            for p in data.get("ports", [])
        ]
        return Checkpoint(
            timestamp=float(data["timestamp"]),
            ports=ports,
            label=data.get("label", ""),
        )


def save_checkpoint(path: Path, ports: List[PortEntry], label: str = "") -> Checkpoint:
    """Write a new checkpoint file and return it."""
    cp = Checkpoint(timestamp=time.time(), ports=list(ports), label=label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cp.to_dict(), indent=2))
    return cp


def load_checkpoint(path: Path) -> Optional[Checkpoint]:
    """Load a checkpoint from *path*, returning None if the file is absent."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Checkpoint.from_dict(data)


def list_checkpoints(directory: Path) -> List[Checkpoint]:
    """Return all checkpoints found in *directory*, sorted oldest-first."""
    checkpoints: List[Checkpoint] = []
    for p in sorted(directory.glob("checkpoint_*.json")):
        cp = load_checkpoint(p)
        if cp is not None:
            checkpoints.append(cp)
    return checkpoints
