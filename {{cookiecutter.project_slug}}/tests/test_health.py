"""Tests for health endpoints."""

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from {{ cookiecutter.package_name }}.core.config import Settings
from {{ cookiecutter.package_name }}.core.constants import Environment
from {{ cookiecutter.package_name }}.core.database import get_session
from {{ cookiecutter.package_name }}.core.health.checks import check_database, check_redis
from {{ cookiecutter.package_name }}.main import app


async def test_live(client: AsyncClient) -> None:
    """Liveness probe returns 200 with status alive."""
    resp = await client.get("/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"
    # No envelope fields
    assert "success" not in body
    assert "data" not in body
    assert "message" not in body
    assert "errors" not in body
    assert "meta" not in body


async def test_ready_healthy(client: AsyncClient) -> None:
    """Readiness probe returns 200 when all dependencies are healthy."""
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"
    # No envelope fields
    assert "success" not in body
    assert "data" not in body
    assert "message" not in body
    assert "errors" not in body
    assert "meta" not in body


async def test_ready_database_failure_unit(mocker: MockerFixture) -> None:
    """check_database returns 'failed' when the database raises."""
    mock_session = mocker.MagicMock()
    mock_session.execute = mocker.AsyncMock(side_effect=Exception("DB down"))

    result = await check_database(mock_session)
    assert result.status == "failed"
    assert result.detail is not None


async def test_ready_database_failure_endpoint(
    client: AsyncClient, mocker: MockerFixture
) -> None:
    """Readiness probe returns 503 (not 500) when database is unavailable.

    Uses dependency_overrides so the entire HTTP path is exercised, including
    exception handlers — the bug was that the old HTTPException path raised
    a ValidationError inside the handler and produced a 500.
    """

    async def broken_session():  # type: ignore[no-untyped-def]
        mock = mocker.AsyncMock(spec=AsyncSession)
        mock.execute.side_effect = Exception("DB down")
        yield mock

    mocker.patch.object(app, "dependency_overrides", {get_session: broken_session})

    resp = await client.get("/ready")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["status"] == "failed"
    # Must not be an envelope response (no success/data/meta fields).
    assert "success" not in body
    assert "data" not in body
    assert "meta" not in body


async def test_health_database_failure_endpoint(
    client: AsyncClient, mocker: MockerFixture
) -> None:
    """Health endpoint returns 503 (not 500) when database is unavailable."""

    async def broken_session():  # type: ignore[no-untyped-def]
        mock = mocker.AsyncMock(spec=AsyncSession)
        mock.execute.side_effect = Exception("DB down")
        yield mock

    mocker.patch.object(app, "dependency_overrides", {get_session: broken_session})

    resp = await client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert body["checks"]["database"]["status"] == "failed"
    assert "version" in body
    assert "success" not in body


async def test_ready_redis_failure_unit(mocker: MockerFixture) -> None:
    """check_redis returns 'failed' when Redis raises."""
    mock_redis = mocker.MagicMock()
    mock_redis.ping = mocker.AsyncMock(side_effect=Exception("Redis down"))

    result = await check_redis(mock_redis)
    assert result.status == "failed"
    assert result.detail is not None


async def test_ready_redis_not_configured() -> None:
    """Readiness probe treats unconfigured Redis as OK."""
    result = await check_redis(None)
    assert result.status == "ok"
    assert result.detail == "not configured"


async def test_health_healthy(client: AsyncClient) -> None:
    """Health endpoint returns 200 with detailed status when healthy."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"
    assert "version" in body
    # No envelope fields
    assert "success" not in body
    assert "data" not in body
    assert "message" not in body
    assert "errors" not in body
    assert "meta" not in body


async def test_health_unhealthy(mocker: MockerFixture) -> None:
    """Health endpoint returns 503 when any dependency fails."""
    mock_session = mocker.MagicMock()
    mock_session.execute = mocker.AsyncMock(side_effect=Exception("DB down"))
    mock_redis = mocker.MagicMock()
    mock_redis.ping = mocker.AsyncMock(side_effect=Exception("Redis down"))

    # This test verifies the check logic; endpoint integration test requires mocking DI
    db_result = await check_database(mock_session)
    redis_result = await check_redis(mock_redis)

    assert db_result.status == "failed"
    assert redis_result.status == "failed"


async def test_database_check_timeout(mocker: MockerFixture) -> None:
    """Database check handles timeout."""
    mock_session = mocker.MagicMock()
    mock_session.execute = mocker.AsyncMock(side_effect=TimeoutError)

    result = await check_database(mock_session, timeout=0.001)
    assert result.status == "failed"
    assert result.detail is not None
    assert "timeout" in result.detail.lower()


async def test_redis_check_timeout(mocker: MockerFixture) -> None:
    """Redis check handles timeout."""
    mock_redis = mocker.MagicMock()
    mock_redis.ping = mocker.AsyncMock(side_effect=TimeoutError)

    result = await check_redis(mock_redis, timeout=0.001)
    assert result.status == "failed"
    assert result.detail is not None
    assert "timeout" in result.detail.lower()


def test_production_settings_reject_dev_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production settings must have a real SECRET_KEY."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings(ENVIRONMENT=Environment.PRODUCTION)
    secure = Settings(ENVIRONMENT=Environment.PRODUCTION, SECRET_KEY="a-real-secret")
    assert secure.is_production is True
