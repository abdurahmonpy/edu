"""Password reset email delivery tests."""

from __future__ import annotations

import asyncio

from backend.app import email
from backend.app.config import settings


def test_reset_email_contains_frontend_token_link(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, username, password):
            captured["login"] = (username, password)

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_username", "mailer")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@example.test")
    monkeypatch.setattr(settings, "public_base_url", "https://englify.example")

    sent = asyncio.run(email.send_password_reset_email("learner@example.test", "reset-token"))

    assert sent is True
    assert captured["connection"] == ("smtp.example.test", 587, 15)
    assert captured["starttls"] is True
    assert captured["login"] == ("mailer", "secret")
    message = captured["message"]
    assert message["To"] == "learner@example.test"
    assert "https://englify.example/kirish?mode=forgot&token=reset-token" in message.get_content()
