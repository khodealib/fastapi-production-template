"""HTTP layer: thin routers that delegate to usecases (no business logic)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from ...core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from ...core.openapi import error_responses
from ...core.pagination import PageParams, page_params
from ...core.response import paginated_response, success_response
from ...infrastructure.ratelimit import rate_limit
from .deps import CurrentUser, RefreshTokenRepo, SuperUser, UserRepo
from .schemas import (
    RefreshRequest,
    TokenResponse,
    TokenResponseEnvelope,
    UserCreate,
    UserListEnvelope,
    UserRead,
    UserReadEnvelope,
)
from .service import (
    AuthenticateUser,
    GetCurrentUser,
    IssueTokenPair,
    ListUsers,
    RefreshAccessToken,
    RegisterUser,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses=error_responses(UnauthorizedError),
)

login_limiter = rate_limit("5/minute", key_prefix="login")
refresh_limiter = rate_limit("20/hour", key_prefix="refresh")
register_limiter = rate_limit("10/hour", key_prefix="register")


@auth_router.post(
    "/register",
    response_model=UserReadEnvelope,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
    responses=error_responses(ConflictError, validation=True),
)
async def register(
    request: Request,
    payload: UserCreate,
    user_repo: UserRepo,
) -> UserReadEnvelope:
    user = await RegisterUser(user_repo).execute(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    return success_response(
        UserRead.model_validate(user),
        message="User registered successfully",
        request=request,
    )


@auth_router.post(
    "/token",
    response_model=TokenResponseEnvelope,
    dependencies=[Depends(login_limiter)],
    responses=error_responses(UnauthorizedError, validation=True),
)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: UserRepo,
    token_repo: RefreshTokenRepo,
) -> TokenResponseEnvelope:
    user = await AuthenticateUser(user_repo).execute(
        email=form.username, password=form.password
    )
    tokens = await IssueTokenPair(user_repo, token_repo).execute(user)
    return success_response(
        TokenResponse(**tokens),
        message="Login successful",
        request=request,
    )


@auth_router.post(
    "/refresh",
    response_model=TokenResponseEnvelope,
    dependencies=[Depends(refresh_limiter)],
    responses=error_responses(UnauthorizedError, validation=True),
)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    user_repo: UserRepo,
    token_repo: RefreshTokenRepo,
) -> TokenResponseEnvelope:
    tokens = await RefreshAccessToken(user_repo, token_repo).execute(
        payload.refresh_token
    )
    return success_response(
        TokenResponse(**tokens),
        message="Token refreshed successfully",
        request=request,
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
    user = await GetCurrentUser(user_repo).execute(user_id)
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
