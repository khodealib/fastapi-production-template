"""Look up a single account by its identifier."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ..models import User
    from ..repositories import UserRepository


class GetUserById:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, user_id: UUID) -> User | None:
        return await self.user_repo.get_by_id(user_id)
