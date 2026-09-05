"""Event handlers for the users module.

Imported by ``application.py`` so the handlers register before the first request.
"""

from __future__ import annotations

import logging

from app.events import subscribe

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

    Uses TaskIQ's ``schedule_by_time`` with a ``RedisScheduleSource`` so the
    scheduler process can discover and enqueue the task after the delay.  The
    handler is a no-op when Redis is not configured (InMemoryBroker in dev/test).
    """
    # Local import avoids a circular import at module load time:
    # events → tasks → broker can form a cycle if imported at the top level.
    from datetime import timedelta

    from taskiq_redis import RedisScheduleSource

    from app.config.settings import get_settings
    from app.modules.users.tasks.welcome import send_welcome_followup_task
    from app.utils.datetime import utcnow

    settings = get_settings()
    if not settings.REDIS_URL:
        logger.debug(
            "REDIS_URL not configured; skipping welcome follow-up schedule for user %s",
            user_id,
        )
        return

    source = RedisScheduleSource(str(settings.REDIS_URL))
    await send_welcome_followup_task.kicker().schedule_by_time(
        source,
        utcnow() + timedelta(hours=3),
        user_id=user_id,
        email=email,
    )
