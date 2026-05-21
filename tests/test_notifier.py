"""Tests for portwatch.notifier."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from portwatch.alerter import ChangeEvent
from portwatch.notifier import EmailNotifier, WebhookNotifier, build_notifiers
from portwatch.scanner import PortEntry


def _event(kind: str = "opened", port: int = 8080) -> ChangeEvent:
    entry = PortEntry(port=port, proto="tcp", local_addr="0.0.0.0", process="python")
    return ChangeEvent(kind=kind, entry=entry)


# ---------------------------------------------------------------------------
# EmailNotifier
# ---------------------------------------------------------------------------

class TestEmailNotifier:
    def test_no_events_skips_smtp(self):
        notifier = EmailNotifier(recipients=["ops@example.com"])
        with patch("smtplib.SMTP") as mock_smtp:
            notifier.notify([])
            mock_smtp.assert_not_called()

    def test_sends_email_on_events(self):
        notifier = EmailNotifier(
            recipients=["ops@example.com"],
            smtp_host="mail.local",
            smtp_port=587,
        )
        with patch("smtplib.SMTP") as mock_smtp_cls:
            ctx = MagicMock()
            mock_smtp_cls.return_value.__enter__ = lambda s: ctx
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.notify([_event()])
            mock_smtp_cls.assert_called_once_with("mail.local", 587)

    def test_subject_contains_event_count(self):
        captured = {}
        notifier = EmailNotifier(recipients=["a@b.com"])

        def fake_send(msg):
            captured["subject"] = msg["Subject"]

        ctx = MagicMock()
        ctx.send_message.side_effect = fake_send

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value.__enter__ = lambda s: ctx
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.notify([_event(), _event(port=9090)])

        assert "2" in captured["subject"]


# ---------------------------------------------------------------------------
# WebhookNotifier
# ---------------------------------------------------------------------------

class TestWebhookNotifier:
    def test_no_events_skips_curl(self):
        notifier = WebhookNotifier(url="http://hook.example.com/alert")
        with patch("subprocess.run") as mock_run:
            notifier.notify([])
            mock_run.assert_not_called()

    def test_calls_curl_on_events(self):
        notifier = WebhookNotifier(url="http://hook.example.com/alert", timeout=5)
        with patch("subprocess.run") as mock_run:
            notifier.notify([_event()])
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "curl" in cmd
            assert "http://hook.example.com/alert" in cmd

    def test_payload_contains_event_info(self):
        notifier = WebhookNotifier(url="http://hook.example.com/alert")
        captured = {}

        def fake_run(cmd, **kwargs):
            data_idx = cmd.index("--data") + 1
            captured["payload"] = json.loads(cmd[data_idx])

        with patch("subprocess.run", side_effect=fake_run):
            notifier.notify([_event(kind="opened", port=8080)])

        assert captured["payload"]["event_count"] == 1
        assert captured["payload"]["events"][0]["port"] == 8080
        assert captured["payload"]["events"][0]["kind"] == "opened"

    def test_extra_headers_added(self):
        notifier = WebhookNotifier(
            url="http://hook.example.com/alert",
            extra_headers=["X-Token: secret"],
        )
        with patch("subprocess.run") as mock_run:
            notifier.notify([_event()])
            cmd = mock_run.call_args[0][0]
            assert "X-Token: secret" in cmd


# ---------------------------------------------------------------------------
# build_notifiers
# ---------------------------------------------------------------------------

class TestBuildNotifiers:
    def test_empty_config_returns_empty_list(self):
        assert build_notifiers() == []

    def test_disabled_email_not_included(self):
        cfg = {"enabled": False, "recipients": ["a@b.com"]}
        result = build_notifiers(email_cfg=cfg)
        assert result == []

    def test_enabled_email_included(self):
        cfg = {"enabled": True, "recipients": ["a@b.com"]}
        result = build_notifiers(email_cfg=cfg)
        assert len(result) == 1
        assert isinstance(result[0], EmailNotifier)

    def test_enabled_webhook_included(self):
        cfg = {"enabled": True, "url": "http://example.com"}
        result = build_notifiers(webhook_cfg=cfg)
        assert len(result) == 1
        assert isinstance(result[0], WebhookNotifier)

    def test_both_enabled(self):
        result = build_notifiers(
            email_cfg={"enabled": True, "recipients": ["x@y.com"]},
            webhook_cfg={"enabled": True, "url": "http://example.com"},
        )
        assert len(result) == 2
