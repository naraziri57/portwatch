"""Tests for portwatch.commands.sampling_cmd."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from portwatch.commands.sampling_cmd import cmd_sampling_record, cmd_sampling_stats
from portwatch.scanner import PortEntry


def _entry(port: int) -> PortEntry:
    return PortEntry(port=port, proto="tcp", address="0.0.0.0", process="svc")


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {
        "store": str(tmp_path / "samples.json"),
        "max_samples": 1440,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCmdSamplingRecord:
    def test_returns_zero_on_success(self, tmp_path):
        with patch("portwatch.commands.sampling_cmd.scan_ports", return_value=[_entry(80)]):
            rc = cmd_sampling_record(_args(tmp_path))
        assert rc == 0

    def test_creates_store_file(self, tmp_path):
        store = tmp_path / "samples.json"
        with patch("portwatch.commands.sampling_cmd.scan_ports", return_value=[]):
            cmd_sampling_record(_args(tmp_path, store=str(store)))
        assert store.exists()

    def test_returns_one_on_scan_failure(self, tmp_path):
        with patch("portwatch.commands.sampling_cmd.scan_ports", side_effect=RuntimeError("fail")):
            rc = cmd_sampling_record(_args(tmp_path))
        assert rc == 1

    def test_output_contains_port_count(self, tmp_path, capsys):
        ports = [_entry(22), _entry(80)]
        with patch("portwatch.commands.sampling_cmd.scan_ports", return_value=ports):
            cmd_sampling_record(_args(tmp_path))
        out = capsys.readouterr().out
        assert "2" in out


class TestCmdSamplingStats:
    def test_returns_zero_when_no_file(self, tmp_path, capsys):
        rc = cmd_sampling_stats(_args(tmp_path))
        assert rc == 0
        assert "no sample" in capsys.readouterr().out

    def test_returns_zero_with_data(self, tmp_path):
        store = tmp_path / "samples.json"
        data = [{"timestamp": 1000.0, "port_count": 3, "ports": []}]
        store.write_text(json.dumps(data))
        rc = cmd_sampling_stats(_args(tmp_path, store=str(store)))
        assert rc == 0

    def test_output_contains_avg_label(self, tmp_path, capsys):
        store = tmp_path / "samples.json"
        data = [{"timestamp": 1000.0, "port_count": 5, "ports": []}]
        store.write_text(json.dumps(data))
        cmd_sampling_stats(_args(tmp_path, store=str(store)))
        out = capsys.readouterr().out
        assert "avg" in out

    def test_output_contains_total_samples(self, tmp_path, capsys):
        store = tmp_path / "samples.json"
        data = [
            {"timestamp": 1000.0, "port_count": 2, "ports": []},
            {"timestamp": 1060.0, "port_count": 4, "ports": []},
        ]
        store.write_text(json.dumps(data))
        cmd_sampling_stats(_args(tmp_path, store=str(store)))
        out = capsys.readouterr().out
        assert "2" in out
