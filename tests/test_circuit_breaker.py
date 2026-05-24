"""Tests for portwatch.circuit_breaker."""
import time
import pytest
from portwatch.circuit_breaker import CircuitBreaker, BreakerState


@pytest.fixture()
def cb() -> CircuitBreaker:
    return CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)


class TestCircuitBreakerValidation:
    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreaker(failure_threshold=0)

    def test_negative_recovery_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreaker(recovery_timeout=-1.0)


class TestCircuitBreakerNormalOperation:
    def test_starts_closed(self, cb):
        assert cb.state == BreakerState.CLOSED

    def test_allows_request_when_closed(self, cb):
        assert cb.allow_request() is True

    def test_success_keeps_closed(self, cb):
        cb.record_success()
        assert cb.state == BreakerState.CLOSED

    def test_failures_below_threshold_stay_closed(self, cb):
        cb.record_failure()
        cb.record_failure()
        assert cb.state == BreakerState.CLOSED

    def test_failures_at_threshold_open(self, cb):
        for _ in range(3):
            cb.record_failure()
        assert cb.state == BreakerState.OPEN

    def test_open_blocks_request(self, cb):
        for _ in range(3):
            cb.record_failure()
        assert cb.allow_request() is False

    def test_success_after_failures_resets(self, cb):
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == BreakerState.CLOSED
        assert cb._failures == 0


class TestCircuitBreakerRecovery:
    def test_transitions_to_half_open_after_timeout(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        assert cb.state == BreakerState.OPEN
        monkeypatch.setattr("portwatch.circuit_breaker.time.monotonic",
                            lambda: cb._opened_at + 2.0)
        assert cb.state == BreakerState.HALF_OPEN

    def test_half_open_allows_request(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        monkeypatch.setattr("portwatch.circuit_breaker.time.monotonic",
                            lambda: cb._opened_at + 2.0)
        assert cb.allow_request() is True

    def test_failure_in_half_open_reopens(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        monkeypatch.setattr("portwatch.circuit_breaker.time.monotonic",
                            lambda: cb._opened_at + 2.0)
        _ = cb.state  # trigger half-open transition
        cb.record_failure()
        assert cb._state == BreakerState.OPEN

    def test_success_in_half_open_closes(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        monkeypatch.setattr("portwatch.circuit_breaker.time.monotonic",
                            lambda: cb._opened_at + 2.0)
        _ = cb.state
        cb.record_success()
        assert cb.state == BreakerState.CLOSED


class TestCircuitBreakerReset:
    def test_manual_reset_closes(self, cb):
        for _ in range(3):
            cb.record_failure()
        cb.reset()
        assert cb.state == BreakerState.CLOSED

    def test_to_dict_contains_state(self, cb):
        d = cb.to_dict()
        assert "state" in d
        assert d["state"] == BreakerState.CLOSED.value

    def test_to_dict_contains_failures(self, cb):
        cb.record_failure()
        assert cb.to_dict()["failures"] == 1
