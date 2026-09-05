"""Rotate a refresh token: verify it, revoke it, issue a fresh pair."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.exceptions.errors import UnauthorizedError
from app.modules.users.metrics import token_refresh_total
from app.security.constants import TOKEN_TYPE_REFRESH
from app.security.jwt import InvalidTokenError, datetime_now_utc, decode_token
from app.utils.hashing import sha256_hex

from .issue_token_pair import IssueTokenPair

if TYPE_CHECKING:
    from app.modules.users.repositories import RefreshTokenRepository, UserRepository


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
            token_refresh_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Invalid refresh token.") from exc

        if payload.get("type") != TOKEN_TYPE_REFRESH or "jti" not in payload:
            token_refresh_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Invalid refresh token.")

        stored = await self.token_repo.get_by_jti_hash(sha256_hex(str(payload["jti"])))
        if stored is None or stored.revoked_at is not None:
            token_refresh_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Refresh token has been revoked.")
        now = datetime_now_utc().replace(tzinfo=None)
        expires_at = stored.expires_at.replace(tzinfo=None)
        if expires_at < now:
            token_refresh_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Refresh token has expired.")

        try:
            user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            token_refresh_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Invalid refresh token.") from exc

        user = await self.user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            token_refresh_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Account is unavailable.")

        await self.token_repo.revoke(stored)
        await self.token_repo.cleanup_expired()
        token_refresh_total.labels(outcome="success").inc()
        return await IssueTokenPair(self.user_repo, self.token_repo).execute(user)
