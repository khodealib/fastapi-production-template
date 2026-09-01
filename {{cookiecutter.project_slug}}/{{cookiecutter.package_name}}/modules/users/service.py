"""Application layer: business usecases. Each usecase does one thing well.

Callers (api layer) depend on these classes, not on repositories directly.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from ...core.config import get_settings
from ...core.exceptions import ConflictError, UnauthorizedError
from ...core.security import (
    TOKEN_SCHEME_BEARER,
    TOKEN_TYPE_REFRESH,
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    datetime_now_utc,
    decode_token,
    hash_password,
    verify_password,
)
from .crud import RefreshTokenRepository, UserRepository

if TYPE_CHECKING:
    from .models import User


class RegisterUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(
        self, *, email: str, password: str, full_name: str | None = None
    ) -> User:
        if await self.user_repo.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists.")
        return await self.user_repo.create(
            email=email, hashed_password=hash_password(password), full_name=full_name
        )


class AuthenticateUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, *, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account is inactive.")
        return user


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
            jti_hash=_hash_jti(jti),
            expires_at=datetime_now_utc()
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return token


class RefreshAccessToken:
    """Rotate a refresh token: verify, revoke old, issue a fresh pair."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def execute(self, raw_token: str) -> dict[str, str]:
        try:
            payload = decode_token(raw_token)
        except (InvalidTokenError, TypeError) as exc:
            raise UnauthorizedError("Invalid refresh token.") from exc

        if payload.get("type") != TOKEN_TYPE_REFRESH or "jti" not in payload:
            raise UnauthorizedError("Invalid refresh token.")

        stored = await self.token_repo.get_by_jti_hash(_hash_jti(str(payload["jti"])))
        if stored is None or stored.revoked_at is not None:
            raise UnauthorizedError("Refresh token has been revoked.")
        now = datetime_now_utc().replace(tzinfo=None)
        expires_at = stored.expires_at.replace(tzinfo=None)
        if expires_at < now:
            raise UnauthorizedError("Refresh token has expired.")

        try:
            user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UnauthorizedError("Invalid refresh token.") from exc

        user = await self.user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Account is unavailable.")

        await self.token_repo.revoke(stored)
        await self.token_repo.cleanup_expired()
        return await IssueTokenPair(self.user_repo, self.token_repo).execute(user)


class GetCurrentUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, user_id: UUID) -> User | None:
        return await self.user_repo.get_by_id(user_id)


class ListUsers:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        return await self.user_repo.list(page=page, page_size=page_size)


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()
