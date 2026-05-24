"""Unit tests for portwatch.profile."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from portwatch.profile import (
    PortProfile,
    diff_profile,
    list_profiles,
    load_profile,
    save_profile,
)
from portwatch.scanner import PortEntry


def _e(port: int, proto: str = "tcp", process: str | None = "svc") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


class TestPortProfile:
    def test_to_dict_contains_name(self):
        p = PortProfile(name="web", ports=[_e(80)])
        assert p.to_dict()["name"] == "web"

    def test_to_dict_contains_ports(self):
        p = PortProfile(name="web", ports=[_e(80), _e(443)])
        assert len(p.to_dict()["ports"]) == 2

    def test_from_dict_roundtrip(self):
        original = PortProfile(name="db", description="database", ports=[_e(5432, "tcp", "postgres")])
        restored = PortProfile.from_dict(original.to_dict())
        assert restored.name == "db"
        assert restored.description == "database"
        assert len(restored.ports) == 1
        assert restored.ports[0].port == 5432

    def test_from_dict_missing_process_is_none(self):
        data = {"name": "x", "ports": [{"port": 22, "proto": "tcp", "address": "0.0.0.0"}]}
        profile = PortProfile.from_dict(data)
        assert profile.ports[0].process is None


def test_save_creates_file(tmp_path):
    p = PortProfile(name="test", ports=[_e(8080)])
    dest = tmp_path / "profiles" / "test.json"
    save_profile(p, dest)
    assert dest.exists()


def test_save_valid_json(tmp_path):
    p = PortProfile(name="test", ports=[_e(8080)])
    dest = tmp_path / "test.json"
    save_profile(p, dest)
    data = json.loads(dest.read_text())
    assert data["name"] == "test"


def test_load_profile_roundtrip(tmp_path):
    p = PortProfile(name="svc", ports=[_e(9000)])
    dest = tmp_path / "svc.json"
    save_profile(p, dest)
    loaded = load_profile(dest)
    assert loaded.name == "svc"
    assert loaded.ports[0].port == 9000


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_profile(tmp_path / "missing.json")


def test_list_profiles_empty(tmp_path):
    assert list_profiles(tmp_path) == []


def test_list_profiles_returns_names(tmp_path):
    for name in ("alpha", "beta", "gamma"):
        save_profile(PortProfile(name=name), tmp_path / f"{name}.json")
    assert list_profiles(tmp_path) == ["alpha", "beta", "gamma"]


class TestDiffProfile:
    def test_no_diff_when_identical(self):
        ports = [_e(80), _e(443)]
        result = diff_profile(PortProfile(name="x", ports=ports), ports)
        assert result["added"] == []
        assert result["removed"] == []

    def test_detects_added_port(self):
        profile = PortProfile(name="x", ports=[_e(80)])
        result = diff_profile(profile, [_e(80), _e(8080)])
        assert any(e.port == 8080 for e in result["added"])

    def test_detects_removed_port(self):
        profile = PortProfile(name="x", ports=[_e(80), _e(22)])
        result = diff_profile(profile, [_e(80)])
        assert any(e.port == 22 for e in result["removed"])
