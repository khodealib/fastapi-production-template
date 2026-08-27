"""Interactors: combine multiple usecases for a single request.

An interactor coordinates multiple repositories and/or usecases in a
single transaction. Unlike usecases (which do one thing), interactors
orchestrate multiple usecases or repositories for complex flows.
"""

from __future__ import annotations

from ...core.security import hash_password
from .crud import RefreshTokenRepository, UserRepository
from .models import User
from .service import IssueTokenPair


class AuthInteractor:
    """Combines user registration with token issuance."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def register_and_issue_tokens(
        self, *, email: str, password: str, full_name: str | None = None
    ) -> tuple[User, dict[str, str]]:
        """Register a new user and immediately issue access/refresh tokens."""
        user = await self.user_repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        tokens = await IssueTokenPair(self.user_repo, self.token_repo).execute(user)
        return user, tokens


class RefreshInteractor:
    """Combines token validation, revocation, and re-issuance."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def rotate_refresh_token(self, raw_token: str) -> dict[str, str]:
        """Verify refresh token, revoke it, and issue new token pair."""
        from ...core.exceptions import UnauthorizedError
        from ...core.security import (
            TOKEN_TYPE_REFRESH,
            InvalidTokenError,
            decode_token,
        )

        try:
            payload = decode_token(raw_token)
        except (InvalidTokenError, TypeError) as exc:
            raise UnauthorizedError("Invalid refresh token.") from exc

        if payload.get("type") != TOKEN_TYPE_REFRESH or "jti" not in payload:
            raise UnauthorizedError("Invalid refresh token.")

        from .service import RefreshAccessToken

        refresh_uc = RefreshAccessToken(self.user_repo, self.token_repo)
        return await refresh_uc.execute(raw_token)
