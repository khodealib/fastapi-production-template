"""Verify a credential pair and return the account behind it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.events import DomainEvent
from app.exceptions.errors import UnauthorizedError
from app.modules.users.events import USER_LOGGED_IN
from app.modules.users.metrics import user_authentication_attempts_total
from app.security.passwords import verify_password

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.users.repositories import UserRepository


class AuthenticateUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(
        self, *, email: str, password: str
    ) -> tuple[User, list[DomainEvent]]:
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            user_authentication_attempts_total.labels(outcome="failure").inc()
            raise UnauthorizedError("Incorrect email or password.")
        if not user.is_active:
            user_authentication_attempts_total.labels(outcome="failure").inc()
            raise UnauthorizedError("This account is inactive.")
        user_authentication_attempts_total.labels(outcome="success").inc()
        return user, [DomainEvent(USER_LOGGED_IN, {"user_id": str(user.id)})]
