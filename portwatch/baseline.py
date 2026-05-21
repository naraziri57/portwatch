"""Baseline management: save and compare against a known-good port snapshot."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from portwatch.scanner import PortEntry
from portwatch.snapshot import load_snapshot, save_snapshot

DEFAULT_BASELINE_PATH = Path(os.environ.get("PORTWATCH_BASELINE", "/var/lib/portwatch/baseline.json"))


def save_baseline(ports: set[PortEntry], path: Path = DEFAULT_BASELINE_PATH) -> None:
    """Persist a set of ports as the trusted baseline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    save_snapshot(ports, path)


def load_baseline(path: Path = DEFAULT_BASELINE_PATH) -> Optional[set[PortEntry]]:
    """Load the baseline from disk.  Returns None if no baseline exists yet."""
    if not path.exists():
        return None
    return load_snapshot(path)


def baseline_exists(path: Path = DEFAULT_BASELINE_PATH) -> bool:
    return path.exists()


def diff_from_baseline(
    current: set[PortEntry],
    path: Path = DEFAULT_BASELINE_PATH,
) -> tuple[set[PortEntry], set[PortEntry]]:
    """Return (new_ports, removed_ports) relative to the stored baseline.

    If no baseline exists, returns (current, empty) — everything is "new".
    """
    baseline = load_baseline(path)
    if baseline is None:
        return current, set()
    new_ports = current - baseline
    removed_ports = baseline - current
    return new_ports, removed_ports
