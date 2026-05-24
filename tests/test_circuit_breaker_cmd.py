"""Tests for portwatch.commands.circuit_breaker_cmd."""
import json
import types
import pytest

import portwatch.commands.circuit_breaker_cmd as cb_cmd
from portwatch.circuit_breaker import BreakerState


@pytest.fixture(autouse=True)
def fresh_breaker():
    """Reset the module-level breaker before each test."""
    cb_cmd._breaker = cb_cmd.CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    yield
    cb_cmd._breaker = cb_cmd.CircuitBreaker()


def _args(**kwargs):
    ns = types.SimpleNamespace(circuit_sub=None, json=False, **kwargs)
    return ns


class TestCmdStatus:
    def test_returns_zero(self, capsys):
        args = _args(circuit_sub="status")
        assert cb_cmd.cmd_circuit_breaker_status(args) == 0

    def test_plain_output_contains_state(self, capsys):
        args = _args(circuit_sub="status")
        cb_cmd.cmd_circuit_breaker_status(args)
        out = capsys.readouterr().out
        assert "closed" in out

    def test_plain_output_contains_failures(self, capsys):
        cb_cmd.get_breaker().record_failure()
        args = _args(circuit_sub="status")
        cb_cmd.cmd_circuit_breaker_status(args)
        out = capsys.readouterr().out
        assert "1/3" in out

    def test_json_output_is_valid(self, capsys):
        args = _args(circuit_sub="status", json=True)
        cb_cmd.cmd_circuit_breaker_status(args)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "state" in data
        assert "failures" in data

    def test_open_state_shown(self, capsys):
        for _ in range(3):
            cb_cmd.get_breaker().record_failure()
        args = _args(circuit_sub="status")
        cb_cmd.cmd_circuit_breaker_status(args)
        out = capsys.readouterr().out
        assert "open" in out


class TestCmdReset:
    def test_returns_zero(self, capsys):
        args = _args(circuit_sub="reset")
        assert cb_cmd.cmd_circuit_breaker_reset(args) == 0

    def test_reset_closes_open_breaker(self, capsys):
        for _ in range(3):
            cb_cmd.get_breaker().record_failure()
        assert cb_cmd.get_breaker().state == BreakerState.OPEN
        args = _args(circuit_sub="reset")
        cb_cmd.cmd_circuit_breaker_reset(args)
        assert cb_cmd.get_breaker().state == BreakerState.CLOSED

    def test_reset_prints_confirmation(self, capsys):
        args = _args(circuit_sub="reset")
        cb_cmd.cmd_circuit_breaker_reset(args)
        out = capsys.readouterr().out
        assert "CLOSED" in out


class TestDispatch:
    def test_no_sub_returns_one(self, capsys):
        args = _args(circuit_sub=None)
        assert cb_cmd._dispatch(args) == 1

    def test_status_dispatched(self, capsys):
        args = _args(circuit_sub="status")
        assert cb_cmd._dispatch(args) == 0

    def test_reset_dispatched(self, capsys):
        args = _args(circuit_sub="reset")
        assert cb_cmd._dispatch(args) == 0
