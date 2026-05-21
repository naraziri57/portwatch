"""Tests for portwatch.baseline."""

from __future__ import annotations

from pathlib import Path

import pytest

from portwatch.baseline import (
    baseline_exists,
    diff_from_baseline,
    load_baseline,
    save_baseline,
)
from portwatch.scanner import PortEntry


@pytest.fixture()
def baseline_path(tmp_path: Path) -> Path:
    return tmp_path / "baseline.json"


@pytest.fixture()
def sample_ports() -> set[PortEntry]:
    return {
        PortEntry(port=22, proto="tcp", state="LISTEN", process="sshd"),
        PortEntry(port=80, proto="tcp", state="LISTEN", process="nginx"),
    }


class TestSaveLoadBaseline:
    def test_save_creates_file(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        save_baseline(sample_ports, baseline_path)
        assert baseline_path.exists()

    def test_roundtrip(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        save_baseline(sample_ports, baseline_path)
        loaded = load_baseline(baseline_path)
        assert loaded == sample_ports

    def test_load_returns_none_when_missing(self, baseline_path: Path) -> None:
        assert load_baseline(baseline_path) is None

    def test_baseline_exists_true(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        save_baseline(sample_ports, baseline_path)
        assert baseline_exists(baseline_path) is True

    def test_baseline_exists_false(self, baseline_path: Path) -> None:
        assert baseline_exists(baseline_path) is False


class TestDiffFromBaseline:
    def test_no_changes(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        save_baseline(sample_ports, baseline_path)
        new, removed = diff_from_baseline(sample_ports, baseline_path)
        assert new == set()
        assert removed == set()

    def test_detects_new_port(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        save_baseline(sample_ports, baseline_path)
        extra = PortEntry(port=443, proto="tcp", state="LISTEN", process="nginx")
        new, removed = diff_from_baseline(sample_ports | {extra}, baseline_path)
        assert extra in new
        assert removed == set()

    def test_detects_removed_port(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        save_baseline(sample_ports, baseline_path)
        reduced = {p for p in sample_ports if p.port != 80}
        new, removed = diff_from_baseline(reduced, baseline_path)
        assert new == set()
        assert any(p.port == 80 for p in removed)

    def test_no_baseline_treats_all_as_new(self, baseline_path: Path, sample_ports: set[PortEntry]) -> None:
        new, removed = diff_from_baseline(sample_ports, baseline_path)
        assert new == sample_ports
        assert removed == set()
