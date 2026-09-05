"""TaskIQ broker — the single broker instance for the application.

Task definitions live in each module's ``tasks/`` package; import ``broker``
from here to register them.

In development (no ``REDIS_URL``), falls back to ``InMemoryBroker`` so the
app starts without a Redis instance.
"""

from __future__ import annotations

from typing import Any

from taskiq import InMemoryBroker
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config.settings import get_settings

settings = get_settings()

if settings.REDIS_URL:
    # The backend is generic over the task return type; tasks vary, so `Any`.
    _result_backend: RedisAsyncResultBackend[Any] = RedisAsyncResultBackend(
        str(settings.REDIS_URL)
    )
    broker = ListQueueBroker(str(settings.REDIS_URL)).with_result_backend(
        _result_backend
    )
else:
    broker = InMemoryBroker()  # type: ignore[assignment]
