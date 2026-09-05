"""Event handlers for the users module.

Imported by ``application.py`` so the handlers register before the first request.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from app.events import subscribe
from app.infrastructure.scheduler import redis_schedule_source
from app.modules.users.tasks.welcome import send_welcome_followup_task
from app.utils.datetime import utcnow

from . import USER_LOGGED_IN, USER_REGISTERED

logger = logging.getLogger(__name__)


@subscribe(USER_REGISTERED)
async def on_user_registered(user_id: str, email: str) -> None:
    """Log the registration; extend to send a welcome email, etc."""
    logger.info("User registered", extra={"user_id": user_id, "email": email})


@subscribe(USER_LOGGED_IN)
async def on_user_logged_in(user_id: str) -> None:
    """Log the login; extend to update last_login, emit metrics, etc."""
    logger.info("User logged in", extra={"user_id": user_id})


@subscribe(USER_REGISTERED)
async def schedule_welcome_followup(user_id: str, email: str) -> None:
    """Kick off the welcome follow-up email, delivered 3 h after registration.

    Uses TaskIQ's ``schedule_by_time`` via ``redis_schedule_source`` from
    ``infrastructure.scheduler``.  A no-op when Redis is not configured.
    """
    if redis_schedule_source is None:
        logger.debug(
            "Redis not configured; skipping welcome follow-up for user %s", user_id
        )
        return

    await send_welcome_followup_task.kicker().schedule_by_time(
        redis_schedule_source,
        utcnow() + timedelta(hours=3),
        user_id=user_id,
        email=email,
    )
