"""Snapshot locking — prevents concurrent writes to snapshot files."""

from __future__ import annotations

import fcntl
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator


DEFAULT_TIMEOUT = 5.0
DEFAULT_POLL_INTERVAL = 0.05


@dataclass
class LockInfo:
    path: Path
    acquired_at: float = field(default_factory=time.monotonic)
    pid: int = field(default_factory=os.getpid)

    def age_seconds(self) -> float:
        return time.monotonic() - self.acquired_at

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "pid": self.pid,
            "age_seconds": self.age_seconds(),
        }


class LockTimeout(Exception):
    """Raised when a lock cannot be acquired within the timeout."""


@contextmanager
def acquire_lock(
    path: Path | str,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> Generator[LockInfo, None, None]:
    """Context manager that holds an exclusive lock on *path*.lock.

    Raises LockTimeout if the lock is not acquired within *timeout* seconds.
    """
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    fd = open(lock_path, "w")  # noqa: WPS515
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockTimeout(
                        f"Could not acquire lock on {lock_path} within {timeout}s"
                    )
                time.sleep(poll_interval)

        info = LockInfo(path=lock_path)
        try:
            yield info
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def is_locked(path: Path | str) -> bool:
    """Return True if the lock file for *path* currently exists."""
    return Path(str(path) + ".lock").exists()
