"""Email helper (stdlib smtplib + Jinja2 templates), runs as a Celery task.

SMTP is optional: helpers no-op when ``SMTP_HOST`` is unset, so local dev and
the test suite don't need a mail server.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.config.settings import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "email"
_jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def render_email(template_name: str, context: dict[str, Any]) -> tuple[str, str | None]:
    """Render ``(text, html)`` from template base files ``.txt`` / ``.html``."""
    body = _jinja.get_template(f"{template_name}.txt").render(**context)
    html_file = TEMPLATES_DIR / f"{template_name}.html"
    html = html_file.read_text().format(**context) if html_file.exists() else None
    return body, html


def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any] | None = None,
    *,
    _client: smtplib.SMTP | smtplib.SMTP_SSL | None = None,
) -> None:
    """Send an email synchronously. Reliable under Celery; no-op w/o SMTP."""
    settings = get_settings()
    if settings.SMTP_HOST is None:
        return

    body, html = render_email(template_name, context or {})
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.set_content(body)
    if html is not None:
        msg.add_alternative(html, subtype="html")

    client = _client
    close = False
    if client is None:
        client = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        close = True
        if settings.SMTP_STARTTLS:
            client.starttls()
        if settings.SMTP_USERNAME:
            client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
    try:
        client.send_message(msg)
    finally:
        if close:
            client.quit()
