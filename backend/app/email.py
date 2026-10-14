"""SMTP delivery for account emails."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from .config import settings


def _send_message(message: EmailMessage) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
        if settings.smtp_starttls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send a one-time password reset link; return False when SMTP is unset."""
    if not settings.smtp_is_configured:
        return False

    reset_url = (
        f"{settings.public_base_url.rstrip('/')}/kirish"
        f"?mode=forgot&token={quote(token, safe='')}"
    )
    message = EmailMessage()
    message["Subject"] = "Englify parolini tiklash"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = email
    message.set_content(
        "Parolingizni tiklash uchun quyidagi havolani oching:\n\n"
        f"{reset_url}\n\n"
        "Havola 30 daqiqa davomida amal qiladi. Agar bu so'rovni siz yubormagan "
        "bo'lsangiz, ushbu xatni e'tiborsiz qoldiring."
    )

    await asyncio.to_thread(_send_message, message)
    return True
