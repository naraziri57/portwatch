"""Tests for portwatch.commands.checkpoint_cmd."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from portwatch.commands.checkpoint_cmd import (
    cmd_checkpoint_diff,
    cmd_checkpoint_list,
    cmd_checkpoint_save,
)
from portwatch.checkpoint import save_checkpoint
from portwatch.scanner import PortEntry


@pytest.fixture()
def sample_ports():
    return [
        PortEntry(port=22, proto="tcp", address="0.0.0.0", process="sshd"),
        PortEntry(port=443, proto="tcp", address="0.0.0.0", process="nginx"),
    ]


@pytest.fixture()
def _args(tmp_path):
    return SimpleNamespace(directory=str(tmp_path), label="")


def test_save_returns_zero(_args, sample_ports):
    with patch("portwatch.commands.checkpoint_cmd.scan_ports", return_value=sample_ports):
        assert cmd_checkpoint_save(_args) == 0


def test_save_creates_file(_args, tmp_path, sample_ports):
    with patch("portwatch.commands.checkpoint_cmd.scan_ports", return_value=sample_ports):
        cmd_checkpoint_save(_args)
    files = list(tmp_path.glob("checkpoint_*.json"))
    assert len(files) == 1


def test_save_with_label(_args, tmp_path, sample_ports):
    _args.label = "pre-deploy"
    with patch("portwatch.commands.checkpoint_cmd.scan_ports", return_value=sample_ports):
        cmd_checkpoint_save(_args)
    files = list(tmp_path.glob("checkpoint_pre-deploy.json"))
    assert len(files) == 1


def test_list_empty_prints_message(_args, capsys):
    cmd_checkpoint_list(_args)
    out = capsys.readouterr().out
    assert "no checkpoints" in out


def test_list_shows_checkpoints(tmp_path, sample_ports, capsys):
    save_checkpoint(tmp_path / "checkpoint_a.json", sample_ports, label="a")
    args = SimpleNamespace(directory=str(tmp_path))
    cmd_checkpoint_list(args)
    out = capsys.readouterr().out
    assert "[a]" in out
    assert "2 ports" in out


def test_diff_no_change_returns_zero(tmp_path, sample_ports, capsys):
    p = tmp_path / "checkpoint_x.json"
    save_checkpoint(p, sample_ports)
    args = SimpleNamespace(checkpoint_a=str(p), checkpoint_b=str(p))
    assert cmd_checkpoint_diff(args) == 0
    assert "no differences" in capsys.readouterr().out


def test_diff_detects_added_port(tmp_path, sample_ports, capsys):
    pa = tmp_path / "cp_a.json"
    pb = tmp_path / "cp_b.json"
    save_checkpoint(pa, sample_ports[:1])
    save_checkpoint(pb, sample_ports)
    args = SimpleNamespace(checkpoint_a=str(pa), checkpoint_b=str(pb))
    rc = cmd_checkpoint_diff(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "+ tcp/443" in out


def test_diff_missing_file_returns_one(tmp_path, sample_ports):
    pa = tmp_path / "cp_a.json"
    save_checkpoint(pa, sample_ports)
    args = SimpleNamespace(checkpoint_a=str(pa), checkpoint_b=str(tmp_path / "nope.json"))
    assert cmd_checkpoint_diff(args) == 1
