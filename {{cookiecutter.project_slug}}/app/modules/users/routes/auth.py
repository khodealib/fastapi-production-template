"""HTTP layer: registration and token endpoints (no business logic)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.events import dispatch_events
from app.exceptions.errors import ConflictError, UnauthorizedError
from app.http.openapi import error_responses
from app.http.response import success_response
from app.infrastructure.ratelimit import rate_limit
from app.modules.users.deps import RefreshTokenRepo, UserRepo
from app.modules.users.schemas import (
    RefreshRequest,
    TokenResponse,
    TokenResponseEnvelope,
    UserCreate,
    UserRead,
    UserReadEnvelope,
)
from app.modules.users.usecases import (
    AuthenticateUser,
    IssueTokenPair,
    RefreshAccessToken,
    RegisterUser,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])

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
    user, events = await RegisterUser(user_repo).execute(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    await dispatch_events(events)
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
    user, events = await AuthenticateUser(user_repo).execute(
        email=form.username, password=form.password
    )
    await dispatch_events(events)
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
