"""SQLAdmin authentication backend guarded by superuser check."""

from uuid import UUID

from fastapi import Request
from sqladmin.authentication import AuthenticationBackend

from ..modules.users.crud import UserRepository
from .database import SessionFactory
from .security import verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        async with SessionFactory() as session:
            user = await UserRepository(session).get_by_email(username)
            if user and user.is_superuser and verify_password(
                password, user.hashed_password
            ):
                request.session.update({"user_id": str(user.id)})
                return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")
        if not user_id:
            return False
        async with SessionFactory() as session:
            user = await UserRepository(session).get_by_id(UUID(user_id))
            return bool(user and user.is_superuser)
