"""SQLAdmin model views (Django-admin equivalent for the users module)."""

from __future__ import annotations

from sqladmin import ModelView

from .models import RefreshToken, User


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.is_active,
        User.is_superuser,
        User.created_at,
    ]
    column_searchable_list = [User.email, User.full_name]
    column_sortable_list = [User.created_at, User.email]
    column_default_sort = [(User.created_at, True)]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    form_columns = ["email", "full_name", "is_active", "is_superuser"]


class RefreshTokenAdmin(ModelView, model=RefreshToken):
    name = "Refresh Token"
    name_plural = "Refresh Tokens"
    icon = "fa-solid fa-key"
    column_list = [
        RefreshToken.id,
        RefreshToken.user_id,
        RefreshToken.created_at,
        RefreshToken.expires_at,
        RefreshToken.revoked_at,
    ]
    column_sortable_list = [RefreshToken.created_at, RefreshToken.expires_at]
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


def register_admin(admin) -> None:
    admin.add_view(UserAdmin)
    admin.add_view(RefreshTokenAdmin)
