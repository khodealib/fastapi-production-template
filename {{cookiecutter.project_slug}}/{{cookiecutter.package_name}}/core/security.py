from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import UUID4

from .config import get_settings

password_hash = PasswordHash.recommended()

# JWT claim discriminators and the RFC 6749 scheme name — not secrets.
TOKEN_TYPE_ACCESS = "access"  # nosec B105
TOKEN_TYPE_REFRESH = "refresh"  # nosec B105
TOKEN_SCHEME_BEARER = "bearer"  # nosec B105


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(
    subject: str | UUID4,
    token_type: str,
    *,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime_now_utc()
    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + (expires_delta or _default_expiry(token_type, settings)),
    }
    if jti is not None:
        claims["jti"] = jti
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str | UUID4, *, expires_delta: timedelta | None = None
) -> str:
    return create_token(subject, TOKEN_TYPE_ACCESS, expires_delta=expires_delta)


def create_refresh_token(
    subject: str | UUID4,
    *,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    return create_token(
        subject, TOKEN_TYPE_REFRESH, expires_delta=expires_delta, jti=jti
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def _default_expiry(token_type: str, settings: Any) -> timedelta:
    if token_type == TOKEN_TYPE_REFRESH:
        return timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    return timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)


def datetime_now_utc() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "TOKEN_SCHEME_BEARER",
    "TOKEN_TYPE_ACCESS",
    "TOKEN_TYPE_REFRESH",
    "InvalidTokenError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
