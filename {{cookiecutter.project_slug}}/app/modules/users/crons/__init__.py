"""Scheduled background tasks for the users module.

Tasks are scheduled by attaching a ``schedule`` label to a ``@broker.task``.
The ``LabelScheduleSource`` in ``infrastructure/scheduler.py`` reads these
labels when the ``taskiq scheduler`` process starts.

Run the scheduler process alongside the worker::

    make worker      # uv run taskiq worker app.infrastructure.broker:broker
    make scheduler   # uv run taskiq scheduler app.infrastructure.scheduler:scheduler

The scheduler *enqueues* tasks; the worker *executes* them.

Example — cleanup expired refresh tokens daily at 02:00 UTC
------------------------------------------------------------
::

    from app.infrastructure.broker import broker

    @broker.task(
        schedule=[{"cron": "0 2 * * *", "args": [], "kwargs": {}}],
    )
    async def cleanup_expired_refresh_tokens() -> None:
        from app.database.session import get_session
        from app.modules.users.repositories import RefreshTokenRepository

        async for session in get_session():
            await RefreshTokenRepository(session).cleanup_expired()
"""

from __future__ import annotations
