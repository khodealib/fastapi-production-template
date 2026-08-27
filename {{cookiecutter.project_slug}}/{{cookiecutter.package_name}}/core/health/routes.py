"""Cross-cutting app: health / readiness probes."""

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
    summary="Liveness + DB dependency check",
)
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthResponse:
    from {{ cookiecutter.package_name }} import __version__

    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - report failure instead of 500ing
        return HealthResponse(status="degraded", version=__version__, database="down")
    return HealthResponse(status="ok", version=__version__)


@health_router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="K8s liveness probe",
)
async def live() -> dict[str, str]:
    return {"status": "alive"}
