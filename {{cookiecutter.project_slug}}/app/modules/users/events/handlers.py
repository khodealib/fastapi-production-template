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
