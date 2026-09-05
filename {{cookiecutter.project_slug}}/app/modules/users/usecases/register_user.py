"""Create an account, rejecting an email that is already taken."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.events import DomainEvent
from app.exceptions.errors import ConflictError
from app.modules.users.events import USER_REGISTERED
from app.modules.users.metrics import user_registrations_total
from app.security.passwords import hash_password

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.users.repositories import UserRepository


class RegisterUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(
        self, *, email: str, password: str, full_name: str | None = None
    ) -> tuple[User, list[DomainEvent]]:
        if await self.user_repo.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists.")
        user = await self.user_repo.create(
            email=email, hashed_password=hash_password(password), full_name=full_name
        )
        user_registrations_total.inc()
        events = [
            DomainEvent(USER_REGISTERED, {"user_id": str(user.id), "email": user.email})
        ]
        return user, events
