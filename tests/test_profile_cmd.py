"""Tests for portwatch.commands.profile_cmd."""
from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from portwatch.commands.profile_cmd import (
    cmd_profile_check,
    cmd_profile_list,
    cmd_profile_save,
)
from portwatch.profile import PortProfile, save_profile
from portwatch.scanner import PortEntry


def _e(port: int) -> PortEntry:
    return PortEntry(port=port, proto="tcp", address="0.0.0.0", process="svc")


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {"dir": str(tmp_path / "profiles"), "name": "default",
                "description": "", "fail_on_diff": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_save_returns_zero(tmp_path):
    with patch("portwatch.commands.profile_cmd.scan_ports", return_value=[_e(80)]):
        assert cmd_profile_save(_args(tmp_path, name="web")) == 0


def test_save_creates_profile_file(tmp_path):
    with patch("portwatch.commands.profile_cmd.scan_ports", return_value=[_e(80)]):
        cmd_profile_save(_args(tmp_path, name="web"))
    assert (tmp_path / "profiles" / "web.json").exists()


def test_check_no_diff_returns_zero(tmp_path):
    ports = [_e(80)]
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir(parents=True)
    save_profile(PortProfile(name="web", ports=ports), profile_dir / "web.json")
    with patch("portwatch.commands.profile_cmd.scan_ports", return_value=ports):
        assert cmd_profile_check(_args(tmp_path, name="web")) == 0


def test_check_with_diff_no_fail_flag_returns_zero(tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir(parents=True)
    save_profile(PortProfile(name="web", ports=[_e(80)]), profile_dir / "web.json")
    with patch("portwatch.commands.profile_cmd.scan_ports", return_value=[_e(80), _e(8080)]):
        assert cmd_profile_check(_args(tmp_path, name="web", fail_on_diff=False)) == 0


def test_check_with_diff_fail_flag_returns_one(tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir(parents=True)
    save_profile(PortProfile(name="web", ports=[_e(80)]), profile_dir / "web.json")
    with patch("portwatch.commands.profile_cmd.scan_ports", return_value=[_e(80), _e(8080)]):
        assert cmd_profile_check(_args(tmp_path, name="web", fail_on_diff=True)) == 1


def test_check_missing_profile_returns_one(tmp_path):
    assert cmd_profile_check(_args(tmp_path, name="missing")) == 1


def test_list_empty_returns_zero(tmp_path):
    assert cmd_profile_list(_args(tmp_path)) == 0


def test_list_shows_saved_profiles(tmp_path, capsys):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir(parents=True)
    for name in ("alpha", "beta"):
        save_profile(PortProfile(name=name), profile_dir / f"{name}.json")
    cmd_profile_list(_args(tmp_path))
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out
