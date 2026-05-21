"""Configuration loading and validation for portwatch."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATHS = [
    Path("portwatch.json"),
    Path("~/.config/portwatch/config.json").expanduser(),
    Path("/etc/portwatch/config.json"),
]

DEFAULTS: dict[str, Any] = {
    "snapshot_path": "/var/lib/portwatch/snapshot.json",
    "interval": 60,
    "alert_handlers": ["stderr"],
    "log_file": None,
    "filters": [],
}


@dataclass
class Config:
    snapshot_path: str = DEFAULTS["snapshot_path"]
    interval: int = DEFAULTS["interval"]
    alert_handlers: list[str] = field(default_factory=lambda: ["stderr"])
    log_file: str | None = None
    filters: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError(f"interval must be >= 1, got {self.interval}")
        valid_handlers = {"stderr", "log"}
        for h in self.alert_handlers:
            if h not in valid_handlers:
                raise ValueError(f"unknown alert handler: {h!r}")
        if "log" in self.alert_handlers and not self.log_file:
            raise ValueError("log_file must be set when using 'log' handler")


def load_config(path: str | Path | None = None) -> Config:
    """Load config from *path*, falling back to default search paths.

    Returns a Config with defaults if no file is found.
    """
    candidates = [Path(path)] if path else DEFAULT_CONFIG_PATHS

    for candidate in candidates:
        if candidate.exists():
            return _parse_file(candidate)

    return Config()


def _parse_file(path: Path) -> Config:
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in config file {path}: {exc}") from exc

    merged = {**DEFAULTS, **raw}
    return Config(
        snapshot_path=merged["snapshot_path"],
        interval=int(merged["interval"]),
        alert_handlers=list(merged["alert_handlers"]),
        log_file=merged["log_file"],
        filters=list(merged["filters"]),
    )
