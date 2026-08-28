"""Cross-cutting app: health / readiness probes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..response import success_response
from ..schemas import CustomModel, Envelope

health_router = APIRouter(tags=["core"])


class HealthResponse(CustomModel):
    status: str = "ok"
    version: str
    database: str = "ok"


HealthEnvelope = Envelope[HealthResponse]


@health_router.get(
    "/health",
    response_model=HealthEnvelope,
    summary="Liveness + DB dependency check",
)
async def health(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthEnvelope:
    from {{ cookiecutter.package_name }} import __version__

    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
        message = "Service is healthy"
    except Exception:  # noqa: BLE001 - report failure instead of 500ing
        db_status = "down"
        message = "Database unavailable"

    return success_response(
        HealthResponse(
            status="ok" if db_status == "ok" else "degraded",
            version=__version__,
            database=db_status,
        ),
        message=message,
        request=request,
    )


@health_router.get(
    "/live",
    response_model=Envelope[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="K8s liveness probe",
)
async def live(request: Request) -> Envelope[dict[str, str]]:
    return success_response(
        {"status": "alive"},
        message="Service is alive",
        request=request,
    )
