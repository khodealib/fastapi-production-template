"""Concrete repository adapters (data access layer).

No business rules live here — only data access."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RefreshToken, User, stmt_by_email


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

    async def list(self, *, page: int, size: int) -> tuple[list[User], int]:
        total = (
            await self.session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        stmt = (
            select(User)
            .order_by(User.created_at.desc())
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_jti_hash(self, jti_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
        )
        return result.scalar_one_or_none()

    async def create(
        self, *, user_id: UUID, jti_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(user_id=user_id, jti_hash=jti_hash, expires_at=expires_at)
        self.session.add(token)
        await self.session.flush()
        return token

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def cleanup_expired(self) -> None:
        await self.session.execute(
            delete(RefreshToken).where(
                RefreshToken.expires_at < datetime.now(UTC).replace(tzinfo=None)
            )
        )
