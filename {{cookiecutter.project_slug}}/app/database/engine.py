"""The async engine and its lifecycle."""

from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.config.settings import get_settings

settings = get_settings()

# :memory: sqlite (tests) needs a shared connection; a real pool would create
# a separate empty database per connection.
engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    **engine_kwargs,
)


async def dispose_engine() -> None:
    await engine.dispose()
