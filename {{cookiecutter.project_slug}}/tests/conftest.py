"""Pytest fixtures. Env is configured BEFORE any app import so the engine and
settings are test-bound from the start."""

from __future__ import annotations

import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-bytes-long"
os.environ["REDIS_URL"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"


from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from fixture_project.core.database import Base, SessionFactory, engine
from fixture_project.infrastructure.ratelimit import get_rate_limiter, get_storage
from fixture_project.main import app
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest_asyncio.fixture(autouse=True)
async def _reset_db() -> AsyncIterator[None]:
    """Fresh schema + rate-limit counters per test (deterministic isolation)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    get_rate_limiter.cache_clear()
    get_storage.cache_clear()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield SessionFactory
