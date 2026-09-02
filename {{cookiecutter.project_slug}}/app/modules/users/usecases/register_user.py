"""Create an account, rejecting an email that is already taken."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.exceptions.errors import ConflictError
from app.security.passwords import hash_password

from ..metrics import user_registrations_total

if TYPE_CHECKING:
    from ..models import User
    from ..repositories import UserRepository


class RegisterUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(
        self, *, email: str, password: str, full_name: str | None = None
    ) -> User:
        if await self.user_repo.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists.")
        user = await self.user_repo.create(
            email=email, hashed_password=hash_password(password), full_name=full_name
        )
        user_registrations_total.inc()
        return user
