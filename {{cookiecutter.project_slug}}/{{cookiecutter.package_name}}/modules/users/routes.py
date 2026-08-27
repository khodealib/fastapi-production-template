"""HTTP layer: thin routers that delegate to usecases (no business logic)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from ...core.exceptions import NotFoundError
from ...core.pagination import Page, PageParams, page_params
from ...infrastructure.ratelimit import rate_limit
from .crud import RefreshTokenRepository, UserRepository
from .deps import CurrentUser, SuperUser
from .schemas import RefreshRequest, TokenResponse, UserCreate, UserRead
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
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
)
async def register(
    payload: UserCreate,
    session: Session,
) -> UserRead:
    user_repo = UserRepository(session)
    user = await RegisterUser(user_repo).execute(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    return UserRead.model_validate(user)


@auth_router.post(
    "/token",
    response_model=TokenResponse,
    dependencies=[Depends(login_limiter)],
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session,
) -> TokenResponse:
    user_repo = UserRepository(session)
    user = await AuthenticateUser(user_repo).execute(
        email=form.username, password=form.password
    )
    token_repo = RefreshTokenRepository(session)
    tokens = await IssueTokenPair(user_repo, token_repo).execute(user)
    return TokenResponse(**tokens)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(refresh_limiter)],
)
async def refresh(
    payload: RefreshRequest,
    session: Session,
) -> TokenResponse:
    token_repo = RefreshTokenRepository(session)
    user_repo = UserRepository(session)
    tokens = await RefreshAccessToken(user_repo, token_repo).execute(
        payload.refresh_token
    )
    return TokenResponse(**tokens)


@users_router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@users_router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    _: SuperUser,
    session: Session,
) -> UserRead:
    user_repo = UserRepository(session)
    user = await GetCurrentUser(user_repo).execute(user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return UserRead.model_validate(user)


@users_router.get("", response_model=Page[UserRead])
async def list_users(
    _: SuperUser,
    session: Session,
    params: Annotated[PageParams, Depends(page_params)],
) -> Page[UserRead]:
    user_repo = UserRepository(session)
    users, total = await ListUsers(user_repo).execute(
        page=params.page, size=params.size
    )
    return Page.build(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        params=params,
    )
