"""Scheduled background tasks for the users module.

A cron is an ordinary TaskIQ task carrying a ``schedule`` label; the
``LabelScheduleSource`` wired into ``app.infrastructure.scheduler`` discovers it
from the broker's registry and enqueues it at the right time. Run
``make scheduler`` next to ``make worker`` — the scheduler enqueues, the worker
executes.

Example — purge expired refresh tokens daily at 02:00 UTC::

    from app.infrastructure.broker import broker

    @broker.task(schedule=[{"cron": "0 2 * * *"}])
    async def purge_expired_refresh_tokens() -> None:
        ...  # call a repository method

The users module has no scheduled work of its own yet, so this package is empty.
"""

from __future__ import annotations
