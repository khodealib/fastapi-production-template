"""Cross-cutting app: health / readiness probes (bare responses for k8s probes)."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.cache import get_redis
from ..database import get_session
from .checks import check_database, check_redis
from .models import CheckStatus, HealthResponse, LiveResponse, ReadyResponse

health_router = APIRouter(tags=["core"])


@health_router.get(
    "/live",
    response_model=LiveResponse,
    status_code=status.HTTP_200_OK,
    summary="K8s liveness probe — process is alive",
)
async def live() -> LiveResponse:
    """Liveness probe.

    Returns 200 if the application process is running.
    Does NOT check any external dependencies.
    """
    return LiveResponse(status="alive")


@health_router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="K8s readiness probe — ready to serve traffic",
)
async def ready(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReadyResponse:
    """Readiness probe.

    Returns 200 if all critical dependencies are available.
    Returns 503 if any critical dependency is unavailable.

    Checks:
    - PostgreSQL (always required)
    - Redis (if configured via REDIS_URL)
    """
    redis = get_redis()

    # Run checks concurrently
    db_result, redis_result = await asyncio.gather(
        check_database(session),
        check_redis(redis),
    )

    checks: dict[str, CheckStatus] = {
        "database": CheckStatus(status=db_result.status, detail=db_result.detail),
        "redis": CheckStatus(status=redis_result.status, detail=redis_result.detail),
    }

    all_ok = all(c.status == "ok" for c in checks.values())

    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ReadyResponse(
                status="not_ready",
                checks=checks,
            ).model_dump(mode="json"),
        )

    return ReadyResponse(status="ready", checks=checks)


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Detailed health status for monitoring",
)
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthResponse:
    """Detailed health status.

    Returns 200 if healthy, 503 if unhealthy.
    Provides detailed status of all checked dependencies.
    """
    from {{ cookiecutter.package_name }} import __version__

    redis = get_redis()

    # Run checks concurrently
    db_result, redis_result = await asyncio.gather(
        check_database(session),
        check_redis(redis),
    )

    checks: dict[str, CheckStatus] = {
        "database": CheckStatus(status=db_result.status, detail=db_result.detail),
        "redis": CheckStatus(status=redis_result.status, detail=redis_result.detail),
    }

    all_ok = all(c.status == "ok" for c in checks.values())

    response = HealthResponse(
        status="healthy" if all_ok else "unhealthy",
        checks=checks,
        version=__version__,
    )

    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.model_dump(mode="json"),
        )

    return response
