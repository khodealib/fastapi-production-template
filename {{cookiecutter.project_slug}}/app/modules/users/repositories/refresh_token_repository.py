"""Concrete repository adapter for ``RefreshToken`` (data access layer)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from ..models import RefreshToken

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


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
