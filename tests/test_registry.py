"""Tests for portwatch.commands.registry."""
from __future__ import annotations

import argparse

import pytest

from portwatch.commands.registry import dispatch, register_all


@pytest.fixture()
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="portwatch")
    register_all(p)
    return p


class TestRegisterAll:
    def test_watch_subcommand_present(self, parser):
        ns = parser.parse_args(["watch", "--once"])
        assert ns.command == "watch"

    def test_report_subcommand_present(self, parser):
        ns = parser.parse_args(["report"])
        assert ns.command == "report"

    def test_baseline_subcommand_present(self, parser):
        ns = parser.parse_args(["baseline", "save"])
        assert ns.command == "baseline"

    def test_func_set_for_watch(self, parser):
        ns = parser.parse_args(["watch"])
        assert callable(ns.func)

    def test_func_set_for_report(self, parser):
        ns = parser.parse_args(["report"])
        assert callable(ns.func)

    def test_func_set_for_baseline(self, parser):
        ns = parser.parse_args(["baseline", "save"])
        assert callable(ns.func)


class TestDispatch:
    def test_dispatch_calls_func(self):
        mock_called = []

        def fake_func(args):
            mock_called.append(args)
            return 42

        ns = argparse.Namespace(func=fake_func)
        rc = dispatch(ns)
        assert rc == 42
        assert len(mock_called) == 1

    def test_dispatch_passes_namespace_to_func(self):
        """Ensure dispatch passes the full Namespace object to the handler."""
        received = []
        ns = argparse.Namespace(func=lambda args: received.append(args))
        dispatch(ns)
        assert received[0] is ns

    def test_dispatch_no_func_returns_1(self):
        ns = argparse.Namespace()
        assert dispatch(ns) == 1

    def test_dispatch_propagates_return_code(self):
        ns = argparse.Namespace(func=lambda _: 7)
        assert dispatch(ns) == 7
