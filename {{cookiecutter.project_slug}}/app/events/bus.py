"""In-process async event bus (Django-signal equivalent).

Usage
-----
Publishing (from a use case, after the side-effect succeeds)::

    from app.events import bus

    await bus.publish("users.registered", user_id=str(user.id), email=user.email)

Subscribing (in a module's ``events/handlers.py``)::

    from app.events import subscribe

    from . import USER_REGISTERED

    @subscribe(USER_REGISTERED)
    async def on_user_registered(user_id: str, email: str) -> None:
        ...

The bus is in-process only: handlers run inside the publishing request. For work
that must survive the response, publish nothing and enqueue a TaskIQ task from
``app.infrastructure.broker`` instead.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Registry of async handlers keyed by event name."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event: str) -> Callable[[Handler], Handler]:
        """Decorator that registers an async handler for *event*."""

        def decorator(fn: Handler) -> Handler:
            self._handlers[event].append(fn)
            return fn

        return decorator

    async def publish(self, event: str, **kwargs: Any) -> None:
        """Fire every handler registered for *event*, gathering exceptions.

        Handlers run concurrently and a failing one is logged rather than
        raised, so one broken subscriber cannot fail the publisher's request.
        """
        handlers = self._handlers.get(event, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *(handler(**kwargs) for handler in handlers), return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                # `event` is reserved by the structlog formatter for the message.
                logger.error(
                    "Event handler raised an exception",
                    exc_info=result,
                    extra={"event_name": event},
                )


bus = EventBus()
subscribe = bus.subscribe
