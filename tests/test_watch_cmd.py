"""Tests for portwatch.commands.watch_cmd."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from portwatch.commands.watch_cmd import cmd_watch, register_subcommands


@pytest.fixture()
def base_args() -> argparse.Namespace:
    return argparse.Namespace(
        config=None,
        interval=None,
        once=False,
    )


def _run(args: argparse.Namespace) -> int:
    return cmd_watch(args)


class TestCmdWatch:
    def test_once_returns_zero_on_success(self, base_args, tmp_path):
        base_args.once = True
        with patch("portwatch.commands.watch_cmd.Watcher") as MockWatcher:
            instance = MockWatcher.return_value
            instance.run_once.return_value = []  # no events, but not None
            rc = _run(base_args)
        assert rc == 0

    def test_once_returns_one_on_scan_failure(self, base_args):
        base_args.once = True
        with patch("portwatch.commands.watch_cmd.Watcher") as MockWatcher:
            instance = MockWatcher.return_value
            instance.run_once.return_value = None  # scanner failed
            rc = _run(base_args)
        assert rc == 1

    def test_bad_config_path_returns_2(self, base_args, tmp_path):
        base_args.config = str(tmp_path / "missing.toml")
        rc = _run(base_args)
        assert rc == 2

    def test_invalid_interval_override_returns_2(self, base_args):
        base_args.interval = -5.0
        rc = _run(base_args)
        assert rc == 2

    def test_start_called_when_not_once(self, base_args):
        with patch("portwatch.commands.watch_cmd.Watcher") as MockWatcher:
            instance = MockWatcher.return_value
            instance.start.side_effect = KeyboardInterrupt
            rc = _run(base_args)
        instance.start.assert_called_once()
        instance.stop.assert_called_once()
        assert rc == 0

    def test_interval_override_applied(self, base_args):
        base_args.interval = 10.0
        base_args.once = True
        with patch("portwatch.commands.watch_cmd.Watcher") as MockWatcher:
            instance = MockWatcher.return_value
            instance.run_once.return_value = []
            _run(base_args)
            _, kwargs = MockWatcher.call_args
            assert kwargs["interval"] == 10.0


def test_register_adds_watch_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_subcommands(sub)
    ns = parser.parse_args(["watch", "--once"])
    assert ns.once is True
    assert ns.func is cmd_watch
