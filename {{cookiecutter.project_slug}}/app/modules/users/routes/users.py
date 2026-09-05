"""HTTP layer: user resource endpoints (no business logic)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.exceptions.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.http.openapi import error_responses
from app.http.pagination import PageParams, page_params
from app.http.response import paginated_response, success_response
from app.modules.users.deps import CurrentUser, SuperUser, UserRepo
from app.modules.users.schemas import UserListEnvelope, UserRead, UserReadEnvelope
from app.modules.users.usecases import GetUserById, ListUsers

users_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses=error_responses(UnauthorizedError),
)


@users_router.get("/me", response_model=UserReadEnvelope)
async def me(request: Request, current_user: CurrentUser) -> UserReadEnvelope:
    return success_response(
        UserRead.model_validate(current_user),
        message="Current user retrieved",
        request=request,
    )


@users_router.get(
    "/{user_id}",
    response_model=UserReadEnvelope,
    responses=error_responses(ForbiddenError, NotFoundError, validation=True),
)
async def get_user(
    request: Request,
    user_id: UUID,
    _: SuperUser,
    user_repo: UserRepo,
) -> UserReadEnvelope:
    user = await GetUserById(user_repo).execute(user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return success_response(
        UserRead.model_validate(user),
        message="User retrieved",
        request=request,
    )


@users_router.get(
    "",
    response_model=UserListEnvelope,
    responses=error_responses(ForbiddenError, validation=True),
)
async def list_users(
    request: Request,
    _: SuperUser,
    user_repo: UserRepo,
    params: Annotated[PageParams, Depends(page_params)],
) -> UserListEnvelope:
    users, total = await ListUsers(user_repo).execute(
        page=params.page, page_size=params.page_size
    )
    return paginated_response(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        params=params,
        message="Users retrieved",
        request=request,
    )
