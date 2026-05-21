"""Notification backends for portwatch alerts."""

from __future__ import annotations

import smtplib
import subprocess
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import List, Optional

from portwatch.alerter import ChangeEvent


@dataclass
class EmailNotifier:
    """Send alert emails via SMTP."""

    recipients: List[str]
    sender: str = "portwatch@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    subject_prefix: str = "[portwatch]"

    def notify(self, events: List[ChangeEvent]) -> None:
        if not events:
            return
        body_lines = [str(e) for e in events]
        body = "\n".join(body_lines)
        subject = f"{self.subject_prefix} {len(events)} port change(s) detected"

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.send_message(msg)


@dataclass
class WebhookNotifier:
    """POST alert payloads to a webhook URL using curl."""

    url: str
    timeout: int = 10
    extra_headers: List[str] = field(default_factory=list)

    def notify(self, events: List[ChangeEvent]) -> None:
        if not events:
            return
        import json

        payload = json.dumps(
            {
                "event_count": len(events),
                "events": [
                    {
                        "kind": e.kind,
                        "port": e.entry.port,
                        "proto": e.entry.proto,
                        "process": e.entry.process,
                    }
                    for e in events
                ],
            }
        )

        cmd = [
            "curl",
            "-s",
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "--max-time", str(self.timeout),
            "--data", payload,
        ]
        for h in self.extra_headers:
            cmd += ["-H", h]
        cmd.append(self.url)

        subprocess.run(cmd, check=False)


def build_notifiers(
    email_cfg: Optional[dict] = None,
    webhook_cfg: Optional[dict] = None,
) -> list:
    """Construct enabled notifiers from config dicts."""
    notifiers = []
    if email_cfg and email_cfg.get("enabled"):
        notifiers.append(
            EmailNotifier(
                recipients=email_cfg["recipients"],
                sender=email_cfg.get("sender", "portwatch@localhost"),
                smtp_host=email_cfg.get("smtp_host", "localhost"),
                smtp_port=int(email_cfg.get("smtp_port", 25)),
            )
        )
    if webhook_cfg and webhook_cfg.get("enabled"):
        notifiers.append(
            WebhookNotifier(
                url=webhook_cfg["url"],
                timeout=int(webhook_cfg.get("timeout", 10)),
                extra_headers=webhook_cfg.get("headers", []),
            )
        )
    return notifiers
