"""Reusable auth dependencies (mirror Django's ``request.user`` / permission checks)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.database.session import Session
from app.exceptions.errors import ForbiddenError, UnauthorizedError
from app.security.constants import TOKEN_TYPE_ACCESS
from app.security.jwt import decode_token

from .models import User
from .repositories import RefreshTokenRepository, UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_user_repository(session: Session) -> UserRepository:
    return UserRepository(session)


def get_refresh_token_repository(session: Session) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
RefreshTokenRepo = Annotated[
    RefreshTokenRepository, Depends(get_refresh_token_repository)
]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: UserRepo,
) -> User:
    credentials_error = UnauthorizedError("Could not validate credentials.")
    try:
        payload = decode_token(token)
    except InvalidTokenError as exc:
        raise credentials_error from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS or "sub" not in payload:
        raise credentials_error
    try:
        user_id = UUID(payload["sub"])
    except (TypeError, ValueError):
        raise credentials_error from None

    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


async def require_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise ForbiddenError("Staff privileges are required.")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
SuperUser = Annotated[User, Depends(require_superuser)]
