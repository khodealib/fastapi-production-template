"""Concrete repository adapter for ``User`` (data access layer).

No business rules live here — only data access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from ..models import User, stmt_by_email

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(stmt_by_email(email))
        return result.scalar_one_or_none()

    async def create(
        self, *, email: str, hashed_password: str, full_name: str | None = None
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def list(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        total = (
            await self.session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        stmt = (
            select(User)
            .order_by(User.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
