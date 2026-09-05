"""Email background tasks for the users module."""

from __future__ import annotations

from typing import Any

from app.infrastructure.broker import broker
from app.infrastructure.email import send_email


@broker.task(retry_on_error=True, max_retries=3)
async def send_email_task(
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any] | None = None,
) -> bool:
    """Send an email in the background."""
    send_email(to, subject, template_name, context)
    return True
