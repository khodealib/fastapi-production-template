"""TaskIQ scheduler — the single scheduler instance for the application.

Scheduled task definitions live in each module's ``crons/`` package; they are
ordinary ``@broker.task`` functions carrying a ``schedule`` label, which
``LabelScheduleSource`` discovers from the broker's task registry.

Run it as its own process, alongside the worker::

    make scheduler   # uv run taskiq scheduler app.infrastructure.scheduler:scheduler

The scheduler only *enqueues* tasks; a worker still has to execute them.
"""

from __future__ import annotations

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.infrastructure.broker import broker

scheduler = TaskiqScheduler(broker=broker, sources=[LabelScheduleSource(broker)])
