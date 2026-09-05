"""Event handlers for the users module.

Imported by ``application.py`` so the handlers register before the first request.

Example — delayed task triggered by an event
---------------------------------------------
To send a follow-up email 3 hours after registration, add a handler that kicks
off a TaskIQ task with ``schedule_by_time``::

    from datetime import timedelta

    from app.infrastructure.scheduler import redis_schedule_source
    from app.modules.users.tasks.welcome import send_welcome_followup_task
    from app.utils.datetime import utcnow

    @subscribe(USER_REGISTERED)
    async def schedule_welcome_followup(user_id: str, email: str) -> None:
        if redis_schedule_source is None:
            return  # no Redis in dev/test — skip silently
        await send_welcome_followup_task.kicker().schedule_by_time(
            redis_schedule_source,
            utcnow() + timedelta(hours=3),
            user_id=user_id,
            email=email,
        )
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
