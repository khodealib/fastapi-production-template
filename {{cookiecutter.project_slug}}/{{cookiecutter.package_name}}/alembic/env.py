"""Alembic environment — wired to app settings + metadata naming convention.

Runs async in SQLite-less setups and sync/async transparently via ``run_sync``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from {{ cookiecutter.package_name }}.core.config import get_settings
from {{ cookiecutter.package_name }}.core.database import Base
from {{ cookiecutter.package_name }}.modules.users import models as _users_models  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()


def _get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(_get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
