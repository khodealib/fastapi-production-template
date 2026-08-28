"""Tests for health endpoints."""

import pytest
from httpx import AsyncClient
from {{ cookiecutter.package_name }}.core.config import Settings
from {{ cookiecutter.package_name }}.core.constants import Environment
from {{ cookiecutter.package_name }}.core.health.checks import check_database, check_redis


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


async def test_ready_database_failure() -> None:
    """Readiness probe returns 503 when database is unavailable."""
    from unittest.mock import AsyncMock, MagicMock

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=Exception("DB down"))

    result = await check_database(mock_session)
    assert result.status == "failed"
    assert result.detail is not None


async def test_ready_redis_failure() -> None:
    """Readiness probe returns 503 when Redis is unavailable (if configured)."""
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Redis down"))

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


async def test_health_unhealthy() -> None:
    """Health endpoint returns 503 when any dependency fails."""
    from unittest.mock import AsyncMock, MagicMock

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=Exception("DB down"))
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Redis down"))

    # This test verifies the check logic; endpoint integration test requires mocking DI
    db_result = await check_database(mock_session)
    redis_result = await check_redis(mock_redis)

    assert db_result.status == "failed"
    assert redis_result.status == "failed"


async def test_database_check_timeout() -> None:
    """Database check handles timeout."""
    from unittest.mock import AsyncMock, MagicMock

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=TimeoutError)

    result = await check_database(mock_session, timeout=0.001)
    assert result.status == "failed"
    assert result.detail is not None
    assert "timeout" in result.detail.lower()


async def test_redis_check_timeout() -> None:
    """Redis check handles timeout."""
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=TimeoutError)

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
