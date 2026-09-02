"""Mint an access token alongside a revocable refresh token."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from app.config.settings import get_settings
from app.security.constants import TOKEN_SCHEME_BEARER
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    datetime_now_utc,
)
from app.utils.hashing import sha256_hex

if TYPE_CHECKING:
    from uuid import UUID

    from ..models import User
    from ..repositories import RefreshTokenRepository, UserRepository


class IssueTokenPair:
    """Create an access token + store a revocable refresh token."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def execute(self, user: User) -> dict[str, str]:
        settings = get_settings()
        access_token = create_access_token(user.id)
        refresh_token = await self._create_refresh(user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": TOKEN_SCHEME_BEARER,
            "expires_in": str(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        }

    async def _create_refresh(self, user_id: UUID) -> str:
        jti = secrets.token_urlsafe(32)
        token = create_refresh_token(
            user_id,
            expires_delta=timedelta(days=get_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            jti=jti,
        )
        settings = get_settings()
        await self.token_repo.create(
            user_id=user_id,
            jti_hash=sha256_hex(jti),
            expires_at=datetime_now_utc()
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return token
