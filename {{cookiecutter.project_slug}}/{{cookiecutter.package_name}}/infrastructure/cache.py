"""Redis-backed cache helpers (thin stand-ins for Django's cache framework).

Redis is optional: when ``REDIS_URL`` is unset the helpers no-op so the app
runs without it in dev.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis | None:
    global _redis
    settings = get_settings()
    if _redis is None and settings.REDIS_URL:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Any | None:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except RedisError:
        return None
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, *, ttl: int | None = None) -> None:
    client = get_redis()
    if client is None:
        return
    settings = get_settings()
    with contextlib.suppress(RedisError):
        await client.set(
            key,
            json.dumps(value, default=str),
            ex=ttl if ttl is not None else settings.CACHE_DEFAULT_TTL_SECONDS,
        )


async def cache_delete(key: str) -> None:
    client = get_redis()
    if client is None:
        return
    with contextlib.suppress(RedisError):
        await client.delete(key)


async def cache_clear_pattern(pattern: str) -> None:
    """Delete every key matching ``pattern`` (e.g. ``"users:*"``)."""
    client = get_redis()
    if client is None:
        return
    try:
        async for key in client.scan_iter(match=pattern, count=500):
            await client.delete(key)
    except RedisError:
        pass


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
