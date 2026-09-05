"""Delayed welcome follow-up task for the users module."""

from __future__ import annotations

from app.infrastructure.broker import broker
from app.infrastructure.email import send_email


@broker.task(retry_on_error=True, max_retries=3)
async def send_welcome_followup_task(user_id: str, email: str) -> bool:
    """Send a follow-up welcome email three hours after registration."""
    send_email(
        to=email,
        subject="Getting started — tips for your first week",
        template_name="welcome_followup",
        context={"user_id": user_id},
    )
    return True
