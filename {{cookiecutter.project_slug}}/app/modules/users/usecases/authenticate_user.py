"""Verify a credential pair and return the account behind it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.events import bus
from app.exceptions.errors import UnauthorizedError
from app.security.passwords import verify_password

from ..events import USER_LOGGED_IN
from ..metrics import user_authentication_attempts_total

if TYPE_CHECKING:
    from ..models import User
    from ..repositories import UserRepository


class AuthenticateUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, *, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            user_authentication_attempts_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Incorrect email or password.")
        if not user.is_active:
            user_authentication_attempts_total.labels(outcome="failure").inc()
            raise UnauthorizedError("This account is inactive.")
        user_authentication_attempts_total.labels(outcome="success").inc()
        await bus.publish(USER_LOGGED_IN, user_id=str(user.id))
        return user
