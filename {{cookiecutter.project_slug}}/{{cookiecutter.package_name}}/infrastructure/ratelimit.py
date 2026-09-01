"""Multi-strategy rate limiting built on the battle-tested ``limits`` library.

Strategies: fixed-window, moving-window, sliding-window. Storage is pluggable
via URI (memory in dev/tests, Redis in production for multi-worker
correctness).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import limits
from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from limits import strategies
from limits.storage import storage_from_string

from ..core.config import get_settings
from ..core.exceptions import RateLimitedError

if TYPE_CHECKING:
    from limits.strategies import RateLimiter as _LimitsRateLimiter

ScopedRateLimiter = Callable[[Request], str]


class RateLimitStrategy(StrEnum):
    FIXED_WINDOW = "fixed-window"
    MOVING_WINDOW = "moving-window"
    SLIDING_WINDOW = "sliding-window"


_STRATEGY_CLASSES: dict[RateLimitStrategy, type[_LimitsRateLimiter]] = {
    RateLimitStrategy.FIXED_WINDOW: strategies.FixedWindowRateLimiter,
    RateLimitStrategy.MOVING_WINDOW: strategies.MovingWindowRateLimiter,
    RateLimitStrategy.SLIDING_WINDOW: strategies.SlidingWindowCounterRateLimiter,
}


@lru_cache
def get_storage(uri: str) -> Any:
    """Return a storage backend. Redis when a URI is given, else memory."""
    return storage_from_string(uri)


@lru_cache
def get_rate_limiter(uri: str, strategy: RateLimitStrategy) -> _LimitsRateLimiter:
    storage = get_storage(uri)
    try:
        cls = _STRATEGY_CLASSES[strategy]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Unsupported rate-limit strategy: {strategy}") from exc
    return cls(storage)


def _parse_strategy(value: str) -> RateLimitStrategy:
    """Resolve RATE_LIMIT_STRATEGY, naming the valid options when it's wrong.

    This runs at import time (route decoration), so a bare ValueError here would
    surface as an unimportable app with no hint at the cause.
    """
    try:
        return RateLimitStrategy(value)
    except ValueError as exc:
        valid = ", ".join(s.value for s in RateLimitStrategy)
        raise ValueError(
            f"Invalid RATE_LIMIT_STRATEGY {value!r}. Valid options: {valid}."
        ) from exc


def _scope_by_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def build_key(
    key_prefix: str,
    request: Request,
    scope: ScopedRateLimiter = _scope_by_ip,
    *,
    per_path: bool = True,
) -> str:
    """Bucket key for a request. Omitting the path shares one budget app-wide."""
    if per_path:
        return f"{key_prefix}:{request.url.path}:{scope(request)}"
    return f"{key_prefix}:{scope(request)}"


def rate_limit(
    item: str,
    *,
    strategy: RateLimitStrategy | None = None,
    scope: ScopedRateLimiter = _scope_by_ip,
    key_prefix: str = "rl",
    per_path: bool = True,
) -> Callable[[Request], Any]:
    """FastAPI dependency enforcing ``item`` (e.g. ``"10/minute"``).

    Strategy and storage come from settings unless overridden per call, so a
    single route can opt into a different algorithm::

        strict = rate_limit(
            "3/minute",
            strategy=RateLimitStrategy.MOVING_WINDOW,
            key_prefix="password_reset",
        )

        @router.post("/reset", dependencies=[Depends(strict)])

    ``per_path`` decides whether each route counts separately (the default) or
    every route shares one bucket per client — what an app-wide budget needs.
    Layering is fine: a router-level dependency runs before the route's own, so
    the narrower limit is the one reported in the ``X-RateLimit-*`` headers.

    The outcome is stashed on ``request.state.rate_limit`` for
    RateLimitHeadersMiddleware.
    """
    settings = get_settings()
    strategy = strategy or _parse_strategy(settings.RATE_LIMIT_STRATEGY)
    rate = limits.parse(item)

    async def dependency(request: Request) -> None:
        limiter = get_rate_limiter(settings.RATE_LIMIT_STORAGE_URI, strategy)
        key = build_key(key_prefix, request, scope, per_path=per_path)
        allowed = await run_in_threadpool(limiter.hit, rate, key)
        reset_ts, remaining = await run_in_threadpool(
            limiter.get_window_stats, rate, key
        )

        if not allowed:
            raise RateLimitedError(retry_after=max(1, int(reset_ts - time.time())))

        request.state.rate_limit = {
            "limit": rate.amount,
            "remaining": remaining,
            "reset": int(reset_ts),
        }

    return dependency
