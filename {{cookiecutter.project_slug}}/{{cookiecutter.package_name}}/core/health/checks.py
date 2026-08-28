"""Health check implementations for infrastructure dependencies."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from redis.asyncio import Redis


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a single health check."""

    name: str
    status: Literal["ok", "failed"]
    detail: str | None = None


async def check_database(session: AsyncSession, timeout: float = 2.0) -> CheckResult:  # noqa: ASYNC109
    """Check database connectivity with a lightweight query.

    Args:
        session: SQLAlchemy async session
        timeout: Timeout in seconds for the check

    Returns:
        CheckResult with status and optional detail
    """
    try:
        async with asyncio.timeout(timeout):
            await session.execute(text("SELECT 1"))
        return CheckResult(name="database", status="ok")
    except TimeoutError:
        return CheckResult(name="database", status="failed", detail="timeout")
    except SQLAlchemyError as e:
        return CheckResult(name="database", status="failed", detail=str(e))
    except Exception as e:  # noqa: BLE001 - catch all to avoid probe crashes
        return CheckResult(name="database", status="failed", detail=f"unexpected: {e}")


async def check_redis(  # noqa: ASYNC109
    redis: Redis | None, timeout: float = 2.0
) -> CheckResult:
    """Check Redis connectivity with PING.

    Args:
        redis: Redis async client (None if not configured)
        timeout: Timeout in seconds for the check

    Returns:
        CheckResult with status and optional detail
    """
    if redis is None:
        return CheckResult(name="redis", status="ok", detail="not configured")

    try:
        async with asyncio.timeout(timeout):
            await redis.ping()
        return CheckResult(name="redis", status="ok")
    except TimeoutError:
        return CheckResult(name="redis", status="failed", detail="timeout")
    except Exception as e:  # noqa: BLE001 - catch all to avoid probe crashes
        with suppress(Exception):
            await redis.aclose()
        return CheckResult(name="redis", status="failed", detail=str(e))
