"""Scheduled background tasks for the users module.

Tasks are scheduled by attaching a ``schedule`` label to a ``@broker.task``.
The ``LabelScheduleSource`` in ``infrastructure/scheduler.py`` reads these
labels when the ``taskiq scheduler`` process starts.

Example — send a daily digest to all active users at 08:00 UTC::

    from app.infrastructure.broker import broker

    @broker.task(
        schedule=[{"cron": "0 8 * * *", "args": [], "kwargs": {}}],
    )
    async def send_daily_digest() -> None:
        ...  # query active users, send digest email

The users module has no scheduled work of its own yet, so this package is empty.
"""

from __future__ import annotations
