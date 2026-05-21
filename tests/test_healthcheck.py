"""Tests for portwatch.healthcheck."""

from __future__ import annotations

import json
import time

import pytest

from portwatch.healthcheck import HealthStatus, check_healthy


@pytest.fixture()
def status() -> HealthStatus:
    return HealthStatus()


class TestHealthStatusDefaults:
    def test_alive_by_default(self, status: HealthStatus) -> None:
        assert status.alive is True

    def test_no_last_scan_by_default(self, status: HealthStatus) -> None:
        assert status.last_scan_ts is None

    def test_no_error_by_default(self, status: HealthStatus) -> None:
        assert status.last_error is None

    def test_port_count_zero_by_default(self, status: HealthStatus) -> None:
        assert status.last_scan_port_count == 0


class TestRecordScan:
    def test_updates_port_count(self, status: HealthStatus) -> None:
        status.record_scan(42)
        assert status.last_scan_port_count == 42

    def test_updates_timestamp(self, status: HealthStatus) -> None:
        before = time.time()
        status.record_scan(5)
        assert status.last_scan_ts is not None
        assert status.last_scan_ts >= before

    def test_clears_previous_error(self, status: HealthStatus) -> None:
        status.record_error("oops")
        status.record_scan(1)
        assert status.last_error is None


class TestRecordError:
    def test_stores_message(self, status: HealthStatus) -> None:
        status.record_error("connection refused")
        assert status.last_error == "connection refused"

    def test_overrides_previous_error(self, status: HealthStatus) -> None:
        status.record_error("first")
        status.record_error("second")
        assert status.last_error == "second"


class TestToDict:
    def test_returns_dict(self, status: HealthStatus) -> None:
        assert isinstance(status.to_dict(), dict)

    def test_no_private_keys(self, status: HealthStatus) -> None:
        d = status.to_dict()
        assert not any(k.startswith("_") for k in d)

    def test_uptime_non_negative(self, status: HealthStatus) -> None:
        assert status.to_dict()["uptime_seconds"] >= 0

    def test_to_json_is_valid(self, status: HealthStatus) -> None:
        payload = json.loads(status.to_json())
        assert "alive" in payload


class TestCheckHealthy:
    def test_healthy_when_alive_no_error(self, status: HealthStatus) -> None:
        assert check_healthy(status) is True

    def test_unhealthy_when_error_present(self, status: HealthStatus) -> None:
        status.record_error("bad")
        assert check_healthy(status) is False

    def test_unhealthy_when_not_alive(self, status: HealthStatus) -> None:
        status.alive = False
        assert check_healthy(status) is False
