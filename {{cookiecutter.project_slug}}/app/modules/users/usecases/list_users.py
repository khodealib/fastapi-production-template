"""Page through the user list."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.users.repositories import UserRepository


class ListUsers:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        return await self.user_repo.list(page=page, page_size=page_size)
