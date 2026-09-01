"""Reusable auth dependencies (mirror Django's ``request.user`` / permission checks)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_session
from ...core.exceptions import ForbiddenError, UnauthorizedError
from ...core.security import TOKEN_TYPE_ACCESS, decode_token
from .crud import UserRepository
from .models import User

Session = Annotated[AsyncSession, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().API_PREFIX}/auth/token",
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session,
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
    except TypeError, ValueError:
        raise credentials_error from None

    user = await UserRepository(session).get_by_id(user_id)
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
