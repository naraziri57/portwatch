"""Port profile management — capture and compare named port snapshots."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from portwatch.scanner import PortEntry


@dataclass
class PortProfile:
    name: str
    description: str = ""
    ports: List[PortEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
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

    @classmethod
    def from_dict(cls, data: dict) -> "PortProfile":
        ports = [
            PortEntry(
                port=p["port"],
                proto=p["proto"],
                address=p["address"],
                process=p.get("process"),
            )
            for p in data.get("ports", [])
        ]
        return cls(name=data["name"], description=data.get("description", ""), ports=ports)


def save_profile(profile: PortProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile.to_dict(), indent=2))


def load_profile(path: Path) -> PortProfile:
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    return PortProfile.from_dict(json.loads(path.read_text()))


def list_profiles(directory: Path) -> List[str]:
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


def diff_profile(profile: PortProfile, current: List[PortEntry]) -> Dict[str, List[PortEntry]]:
    """Return ports that were added or removed compared to the profile."""
    baseline_set = set(profile.ports)
    current_set = set(current)
    return {
        "added": sorted(current_set - baseline_set, key=lambda e: (e.port, e.proto)),
        "removed": sorted(baseline_set - current_set, key=lambda e: (e.port, e.proto)),
    }
