"""Port signature tracking — detect when a port's characteristics change unexpectedly."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

from portwatch.scanner import PortEntry


@dataclass(frozen=True)
class PortSignature:
    """A stable fingerprint of a port's observable characteristics."""

    port: int
    proto: str
    address: str
    process: Optional[str]
    digest: str

    def __str__(self) -> str:
        proc = self.process or "<unknown>"
        return f"{self.proto}:{self.port} @ {self.address} [{proc}] ({self.digest[:8]})"

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "proto": self.proto,
            "address": self.address,
            "process": self.process,
            "digest": self.digest,
        }

    @staticmethod
    def from_dict(d: dict) -> "PortSignature":
        return PortSignature(
            port=d["port"],
            proto=d["proto"],
            address=d["address"],
            process=d.get("process"),
            digest=d["digest"],
        )


def _compute_signature(entry: PortEntry) -> str:
    payload = json.dumps(
        {
            "port": entry.port,
            "proto": entry.proto,
            "address": entry.address,
            "process": entry.process,
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def build_signature(entry: PortEntry) -> PortSignature:
    """Build a PortSignature from a live PortEntry."""
    return PortSignature(
        port=entry.port,
        proto=entry.proto,
        address=entry.address,
        process=entry.process,
        digest=_compute_signature(entry),
    )


@dataclass
class SignatureChange:
    """Describes a mismatch between a known and current signature."""

    port: int
    proto: str
    previous: PortSignature
    current: PortSignature
    changed_fields: list[str] = field(default_factory=list)

    def summary(self) -> str:
        fields = ", ".join(self.changed_fields) if self.changed_fields else "unknown"
        return f"{self.proto}:{self.port} signature changed ({fields})"


def detect_signature_changes(
    known: dict[tuple[int, str], PortSignature],
    current_entries: list[PortEntry],
) -> list[SignatureChange]:
    """Compare current port entries against known signatures and return any changes."""
    changes: list[SignatureChange] = []
    for entry in current_entries:
        key = (entry.port, entry.proto)
        if key not in known:
            continue
        prev = known[key]
        curr = build_signature(entry)
        if prev.digest == curr.digest:
            continue
        changed = [
            f for f in ("address", "process")
            if getattr(prev, f) != getattr(curr, f)
        ]
        changes.append(SignatureChange(
            port=entry.port,
            proto=entry.proto,
            previous=prev,
            current=curr,
            changed_fields=changed,
        ))
    return changes
