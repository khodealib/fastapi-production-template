"""TaskIQ scheduler and schedule source — the single scheduler instance.

Scheduled task definitions live in each module's ``crons/`` package; they are
ordinary ``@broker.task`` functions carrying a ``schedule`` label, which
``LabelScheduleSource`` discovers from the broker's task registry.

``redis_schedule_source`` is provided for one-off delayed dispatches from event
handlers (e.g. "send welcome email 3 h after registration").  It is ``None``
when ``REDIS_URL`` is unset (InMemoryBroker in dev/test).

Run it as its own process, alongside the worker::

    make scheduler   # uv run taskiq scheduler app.infrastructure.scheduler:scheduler

The scheduler only *enqueues* tasks; a worker still has to execute them.
"""

from __future__ import annotations

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.config.settings import get_settings
from app.infrastructure.broker import broker

settings = get_settings()

scheduler = TaskiqScheduler(broker=broker, sources=[LabelScheduleSource(broker)])

if settings.REDIS_URL:
    from taskiq_redis import RedisScheduleSource

    redis_schedule_source: RedisScheduleSource | None = RedisScheduleSource(
        str(settings.REDIS_URL)
    )
else:
    redis_schedule_source = None
