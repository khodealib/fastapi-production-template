"""Cross-cutting app: health / readiness probes (bare responses for k8s probes)."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.database.session import get_session
from app.infrastructure.cache import get_redis

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


async def _run_checks(session: AsyncSession) -> tuple[dict[str, CheckStatus], bool]:
    """Run all dependency checks concurrently; return results and overall health."""
    db_result, redis_result = await asyncio.gather(
        check_database(session),
        check_redis(get_redis()),
    )
    checks = {
        "database": CheckStatus(status=db_result.status, detail=db_result.detail),
        "redis": CheckStatus(status=redis_result.status, detail=redis_result.detail),
    }
    return checks, all(c.status == "ok" for c in checks.values())


def _unavailable(payload: ReadyResponse | HealthResponse) -> JSONResponse:
    """503 with the probe body verbatim.

    Deliberately a plain JSONResponse rather than ``raise HTTPException``: these probes
    sit outside the response envelope, and routing them through the app's exception
    handlers would re-wrap them (and fail, since ``ErrorDetail.message`` is a ``str``).
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload.model_dump(mode="json"),
    )


@health_router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="K8s readiness probe — ready to serve traffic",
    responses={
        503: {
            "model": ReadyResponse,
            "description": "A critical dependency is unavailable.",
        }
    },
)
async def ready(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReadyResponse | Response:
    """Readiness probe.

    Returns 200 if all critical dependencies are available.
    Returns 503 if any critical dependency is unavailable.

    Checks:
    - PostgreSQL (always required)
    - Redis (if configured via REDIS_URL)
    """
    checks, all_ok = await _run_checks(session)
    if not all_ok:
        return _unavailable(ReadyResponse(status="not_ready", checks=checks))
    return ReadyResponse(status="ready", checks=checks)


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Detailed health status for monitoring",
    responses={
        503: {
            "model": HealthResponse,
            "description": "At least one dependency check failed.",
        }
    },
)
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthResponse | Response:
    """Detailed health status.

    Returns 200 if healthy, 503 if unhealthy.
    Provides detailed status of all checked dependencies.
    """
    checks, all_ok = await _run_checks(session)
    response = HealthResponse(
        status="healthy" if all_ok else "unhealthy",
        checks=checks,
        version=__version__,
    )
    if not all_ok:
        return _unavailable(response)
    return response
