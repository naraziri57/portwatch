"""Tests for portwatch.retention."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from portwatch.retention import RetentionPolicy, apply_retention


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(days_ago: int, port: int = 8080) -> dict:
    ts = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return {"timestamp": ts.isoformat(), "port": port, "kind": "opened"}


def _write_entries(path: Path, entries: list) -> None:
    lines = [json.dumps(e, separators=(",", ":")) for e in entries]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# RetentionPolicy validation
# ---------------------------------------------------------------------------

class TestRetentionPolicyValidation:
    def test_defaults(self):
        p = RetentionPolicy()
        assert p.max_age_days == 30
        assert p.max_entries == 10_000

    def test_zero_days_raises(self):
        with pytest.raises(ValueError, match="max_age_days"):
            RetentionPolicy(max_age_days=0)

    def test_zero_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            RetentionPolicy(max_entries=0)

    def test_negative_days_raises(self):
        with pytest.raises(ValueError):
            RetentionPolicy(max_age_days=-5)


# ---------------------------------------------------------------------------
# apply_retention
# ---------------------------------------------------------------------------

@pytest.fixture()
def audit_file(tmp_path: Path) -> Path:
    return tmp_path / "audit.log"


class TestApplyRetention:
    def test_missing_file_returns_zero(self, audit_file: Path):
        assert apply_retention(audit_file, RetentionPolicy()) == 0

    def test_empty_file_returns_zero(self, audit_file: Path):
        audit_file.write_text("", encoding="utf-8")
        assert apply_retention(audit_file, RetentionPolicy()) == 0

    def test_fresh_entries_kept(self, audit_file: Path):
        entries = [_make_entry(1), _make_entry(2)]
        _write_entries(audit_file, entries)
        removed = apply_retention(audit_file, RetentionPolicy(max_age_days=30))
        assert removed == 0
        remaining = audit_file.read_text().strip().splitlines()
        assert len(remaining) == 2

    def test_old_entries_removed(self, audit_file: Path):
        entries = [_make_entry(40), _make_entry(1)]
        _write_entries(audit_file, entries)
        removed = apply_retention(audit_file, RetentionPolicy(max_age_days=30))
        assert removed == 1
        remaining = audit_file.read_text().strip().splitlines()
        assert len(remaining) == 1

    def test_max_entries_trims_oldest(self, audit_file: Path):
        entries = [_make_entry(1, port=8000 + i) for i in range(10)]
        _write_entries(audit_file, entries)
        removed = apply_retention(audit_file, RetentionPolicy(max_entries=5))
        assert removed == 5
        remaining = audit_file.read_text().strip().splitlines()
        assert len(remaining) == 5

    def test_all_old_entries_clears_file(self, audit_file: Path):
        entries = [_make_entry(100), _make_entry(200)]
        _write_entries(audit_file, entries)
        removed = apply_retention(audit_file, RetentionPolicy(max_age_days=30))
        assert removed == 2
        assert audit_file.read_text() == ""
