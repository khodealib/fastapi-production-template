"""HTTP layer: thin routers that delegate to usecases (no business logic)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from ...core.exceptions import NotFoundError
from ...core.pagination import PageParams, page_params
from ...core.response import paginated_response, success_response
from ...infrastructure.ratelimit import rate_limit
from .crud import RefreshTokenRepository, UserRepository
from .deps import CurrentUser, SuperUser
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
users_router = APIRouter(prefix="/users", tags=["users"])

login_limiter = rate_limit("5/minute", key_prefix="login")
refresh_limiter = rate_limit("20/hour", key_prefix="refresh")
register_limiter = rate_limit("10/hour", key_prefix="register")

Session = Annotated[AsyncSession, Depends(get_session)]


@auth_router.post(
    "/register",
    response_model=UserReadEnvelope,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
)
async def register(
    request: Request,
    payload: UserCreate,
    session: Session,
) -> UserReadEnvelope:
    user_repo = UserRepository(session)
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
)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session,
) -> TokenResponseEnvelope:
    user_repo = UserRepository(session)
    user = await AuthenticateUser(user_repo).execute(
        email=form.username, password=form.password
    )
    token_repo = RefreshTokenRepository(session)
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
)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    session: Session,
) -> TokenResponseEnvelope:
    token_repo = RefreshTokenRepository(session)
    user_repo = UserRepository(session)
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


@users_router.get("/{user_id}", response_model=UserReadEnvelope)
async def get_user(
    request: Request,
    user_id: UUID,
    _: SuperUser,
    session: Session,
) -> UserReadEnvelope:
    user_repo = UserRepository(session)
    user = await GetCurrentUser(user_repo).execute(user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return success_response(
        UserRead.model_validate(user),
        message="User retrieved",
        request=request,
    )


@users_router.get("", response_model=UserListEnvelope)
async def list_users(
    request: Request,
    _: SuperUser,
    session: Session,
    params: Annotated[PageParams, Depends(page_params)],
) -> UserListEnvelope:
    user_repo = UserRepository(session)
    users, total = await ListUsers(user_repo).execute(
        page=params.page, size=params.size
    )
    return paginated_response(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        params=params,
        message="Users retrieved",
        request=request,
    )
