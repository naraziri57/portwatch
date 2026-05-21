"""Tests for portwatch.config."""

import json
from pathlib import Path

import pytest

from portwatch.config import Config, load_config, DEFAULTS


# ---------------------------------------------------------------------------
# Config dataclass validation
# ---------------------------------------------------------------------------

class TestConfigValidation:
    def test_defaults(self):
        cfg = Config()
        assert cfg.interval == DEFAULTS["interval"]
        assert cfg.snapshot_path == DEFAULTS["snapshot_path"]
        assert cfg.alert_handlers == ["stderr"]
        assert cfg.log_file is None
        assert cfg.filters == []

    def test_interval_zero_raises(self):
        with pytest.raises(ValueError, match="interval"):
            Config(interval=0)

    def test_interval_negative_raises(self):
        with pytest.raises(ValueError, match="interval"):
            Config(interval=-5)

    def test_unknown_handler_raises(self):
        with pytest.raises(ValueError, match="unknown alert handler"):
            Config(alert_handlers=["webhook"])

    def test_log_handler_without_log_file_raises(self):
        with pytest.raises(ValueError, match="log_file"):
            Config(alert_handlers=["log"], log_file=None)

    def test_log_handler_with_log_file_ok(self):
        cfg = Config(alert_handlers=["log"], log_file="/tmp/pw.log")
        assert cfg.log_file == "/tmp/pw.log"


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_no_file_returns_defaults():
    """When no config file exists anywhere, defaults are returned."""
    cfg = load_config(path="/nonexistent/portwatch.json")
    assert isinstance(cfg, Config)
    assert cfg.interval == DEFAULTS["interval"]


def test_load_config_reads_file(tmp_path: Path):
    cfg_file = tmp_path / "portwatch.json"
    cfg_file.write_text(json.dumps({"interval": 30, "snapshot_path": "/tmp/snap.json"}))

    cfg = load_config(path=cfg_file)
    assert cfg.interval == 30
    assert cfg.snapshot_path == "/tmp/snap.json"
    # unspecified keys keep defaults
    assert cfg.alert_handlers == ["stderr"]


def test_load_config_invalid_json_raises(tmp_path: Path):
    bad = tmp_path / "portwatch.json"
    bad.write_text("{not valid json")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_config(path=bad)


def test_load_config_full(tmp_path: Path):
    cfg_file = tmp_path / "portwatch.json"
    data = {
        "snapshot_path": "/tmp/s.json",
        "interval": 10,
        "alert_handlers": ["log"],
        "log_file": "/tmp/pw.log",
        "filters": [{"port": 22}],
    }
    cfg_file.write_text(json.dumps(data))
    cfg = load_config(path=cfg_file)
    assert cfg.interval == 10
    assert cfg.log_file == "/tmp/pw.log"
    assert cfg.filters == [{"port": 22}]
