"""Core watch loop: periodically scans ports, diffs against snapshot, fires alerts."""

import time
import logging
from pathlib import Path

from portwatch.scanner import scan_ports
from portwatch.snapshot import load_snapshot, save_snapshot, diff_snapshots
from portwatch.alerter import Alerter, ChangeEvent

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 30  # seconds
DEFAULT_SNAPSHOT_PATH = Path("/var/lib/portwatch/snapshot.json")


class Watcher:
    """Runs the main monitoring loop."""

    def __init__(
        self,
        snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
        interval: int = DEFAULT_INTERVAL,
        alerter: Alerter | None = None,
    ) -> None:
        self.snapshot_path = snapshot_path
        self.interval = interval
        self.alerter = alerter or Alerter()
        self._running = False

    def run_once(self) -> list[ChangeEvent]:
        """Scan ports once, compare to saved snapshot, persist new snapshot.

        Returns list of change events (may be empty on first run).
        """
        current = scan_ports()
        previous = load_snapshot(self.snapshot_path)

        events: list[ChangeEvent] = []
        if previous is not None:
            opened, closed = diff_snapshots(previous, current)
            for port in opened:
                events.append(ChangeEvent(kind="opened", port=port))
            for port in closed:
                events.append(ChangeEvent(kind="closed", port=port))

            for event in events:
                self.alerter.emit(event)
        else:
            logger.info(
                "No previous snapshot found at %s — establishing baseline (%d ports).",
                self.snapshot_path,
                len(current),
            )

        save_snapshot(current, self.snapshot_path)
        return events

    def start(self) -> None:  # pragma: no cover
        """Block forever, calling run_once every self.interval seconds."""
        self._running = True
        logger.info("portwatch started (interval=%ds, snapshot=%s)", self.interval, self.snapshot_path)
        try:
            while self._running:
                self.run_once()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("portwatch stopped.")
            self._running = False

    def stop(self) -> None:  # pragma: no cover
        self._running = False
