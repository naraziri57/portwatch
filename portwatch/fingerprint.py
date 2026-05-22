"""Port fingerprinting — attach a stable fingerprint to each open port entry.

A fingerprint is a short hash derived from the port's key attributes so
that consumers can detect when a port's characteristics change even if
the port number stays the same (e.g. the owning process changes).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Dict

from portwatch.scanner import PortEntry


@dataclass(frozen=True)
class Fingerprint:
    port: int
    proto: str
    process: str
    digest: str  # hex string, first 12 chars of sha256

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "process": self.process,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Fingerprint":
        return cls(
            port=int(data["port"]),
            proto=str(data["proto"]),
            process=str(data["process"]),
            digest=str(data["digest"]),
        )

    def __str__(self) -> str:
        return f"{self.proto}:{self.port} ({self.process}) [{self.digest}]"


def _compute_digest(entry: PortEntry) -> str:
    """Return a 12-character hex digest for a PortEntry."""
    payload = json.dumps(
        {
            "port": entry.port,
            "proto": entry.proto,
            "process": entry.process or "",
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def fingerprint_entry(entry: PortEntry) -> Fingerprint:
    """Build a Fingerprint for a single PortEntry."""
    return Fingerprint(
        port=entry.port,
        proto=entry.proto,
        process=entry.process or "",
        digest=_compute_digest(entry),
    )


def fingerprint_all(entries: Iterable[PortEntry]) -> Dict[tuple, Fingerprint]:
    """Return a mapping of (proto, port) -> Fingerprint for every entry."""
    result: Dict[tuple, Fingerprint] = {}
    for entry in entries:
        key = (entry.proto, entry.port)
        result[key] = fingerprint_entry(entry)
    return result


def changed_fingerprints(
    old: Dict[tuple, Fingerprint],
    new: Dict[tuple, Fingerprint],
) -> list[tuple[Fingerprint, Fingerprint]]:
    """Return (old_fp, new_fp) pairs where the digest changed for the same key."""
    changes = []
    for key, new_fp in new.items():
        if key in old and old[key].digest != new_fp.digest:
            changes.append((old[key], new_fp))
    return changes
