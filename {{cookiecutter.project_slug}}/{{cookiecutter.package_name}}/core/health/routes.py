"""Cross-cutting app: health / readiness probes (bare responses for k8s probes)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..schemas import CustomModel

health_router = APIRouter(tags=["core"])


class HealthResponse(CustomModel):
    status: str = "ok"
    version: str
    database: str = "ok"


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Readiness probe — DB dependency check",
)
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthResponse:
    from {{ cookiecutter.package_name }} import __version__

    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 - report failure instead of 500ing
        db_status = "down"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=__version__,
        database=db_status,
    )


@health_router.get(
    "/live",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="K8s liveness probe",
)
async def live() -> dict[str, str]:
    return {"status": "alive"}
