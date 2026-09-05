"""Background tasks for the users module.

Define tasks with ``@broker.task`` and import them here so the worker
discovers them on startup.

Example — delayed welcome follow-up email
-----------------------------------------
::

    from app.infrastructure.broker import broker
    from app.infrastructure.email import send_email

    @broker.task(retry_on_error=True, max_retries=3)
    async def send_welcome_followup_task(user_id: str, email: str) -> bool:
        send_email(
            to=email,
            subject="Getting started — tips for your first week",
            template_name="welcome_followup",
            context={"user_id": user_id},
        )
        return True

To schedule it 3 hours after registration, see the example in
``events/handlers.py``.
"""

from __future__ import annotations

from .email import send_email_task

__all__ = ["send_email_task"]
