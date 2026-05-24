"""Tests for portwatch.commands.heatmap_cmd."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from portwatch.commands.heatmap_cmd import cmd_heatmap, register_subcommands


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {
        "audit_file": str(tmp_path / "audit.jsonl"),
        "save": "",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_returns_zero_on_empty_audit(tmp_path: Path, capsys):
    rc = cmd_heatmap(_args(tmp_path))
    assert rc == 0
    out = capsys.readouterr().out
    assert "empty" in out.lower()


def test_prints_peak_when_events_present(tmp_path: Path, capsys):
    audit = tmp_path / "audit.jsonl"
    # Write a minimal audit entry manually
    entry = {
        "kind": "opened",
        "timestamp": "2024-06-10T14:30:00",
        "proto": "tcp",
        "port": 8080,
        "address": "0.0.0.0",
        "process": "app",
    }
    audit.write_text(json.dumps(entry) + "\n")

    with patch(
        "portwatch.commands.heatmap_cmd._build_from_audit",
        side_effect=lambda p: _make_heatmap_with_event(),
    ):
        rc = cmd_heatmap(_args(tmp_path, audit_file=str(audit)))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Peak" in out


def _make_heatmap_with_event():
    from datetime import datetime
    from portwatch.heatmap import Heatmap
    h = Heatmap()
    h.record(datetime(2024, 6, 10, 14, 0))
    return h


def test_save_writes_file(tmp_path: Path, capsys):
    out_file = tmp_path / "heatmap.json"
    with patch(
        "portwatch.commands.heatmap_cmd._build_from_audit",
        side_effect=lambda p: _make_heatmap_with_event(),
    ):
        rc = cmd_heatmap(_args(tmp_path, save=str(out_file)))
    assert rc == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "grid" in data


def test_register_subcommands_adds_heatmap():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["heatmap"])
    assert hasattr(ns, "func")


def test_register_accepts_audit_file_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["heatmap", "--audit-file", "custom.jsonl"])
    assert ns.audit_file == "custom.jsonl"


def test_register_accepts_save_flag(tmp_path: Path):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["heatmap", "--save", "out.json"])
    assert ns.save == "out.json"
