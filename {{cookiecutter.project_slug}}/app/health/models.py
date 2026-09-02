"""Pydantic response models for health endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class LiveResponse(BaseModel):
    """Liveness probe response."""

    model_config = ConfigDict(frozen=True)

    status: Literal["alive"]


class CheckStatus(BaseModel):
    """Individual dependency check status."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "failed"]
    detail: str | None = None


class ReadyResponse(BaseModel):
    """Readiness probe response."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "not_ready"]
    checks: dict[str, CheckStatus]


class HealthResponse(BaseModel):
    """Detailed health status response."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "unhealthy"]
    checks: dict[str, CheckStatus]
    version: str
