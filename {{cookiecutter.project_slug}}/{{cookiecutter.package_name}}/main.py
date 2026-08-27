"""Application factory + root wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from .api import api_router
from .core.config import get_settings
from .core.constants import Environment
from .core.database import SessionFactory, dispose_engine, engine
from .core.exceptions import AppError
from .core.health import health_router
from .core.logging_conf import configure_logging
from .core.security import verify_password
from .infrastructure.cache import close_redis
from .middleware import (
    RateLimitHeadersMiddleware,
    RequestContextMiddleware,
)
from .modules.users.admin import register_admin
from .modules.users.crud import UserRepository

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class AdminAuth(AuthenticationBackend):
    """Guard /admin behind the same User superuser model (Django-admin parity)."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        async with SessionFactory() as session:
            user = await UserRepository(session).get_by_email(username)
            if (
                user
                and user.is_superuser
                and verify_password(password, user.hashed_password)
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


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.LOG_LEVEL, json=settings.LOG_JSON)

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,  # noqa: ARG001 - signature fixed by FastAPI
    ) -> AsyncIterator[None]:
        settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        yield
        await dispose_engine()
        await close_redis()

    app_configs: dict[str, Any] = {
        "title": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "lifespan": lifespan,
    }
    # Hide interactive docs outside dev/staging (per best practices).
    if settings.ENVIRONMENT not in (Environment.DEVELOPMENT, Environment.TEST):
        app_configs["openapi_url"] = None

    app = FastAPI(**app_configs)

    # --- middleware -----------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitHeadersMiddleware)

    # --- routers --------------------------------------------------------------
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # --- error handling -------------------------------------------------------
    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,  # noqa: ARG001 - signature fixed by Starlette
        exc: AppError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, **exc.extra},
        )

    # --- admin (Django /admin equivalent) -------------------------------------
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=AdminAuth(secret_key=settings.SECRET_KEY),
        title=f"{settings.APP_NAME} Admin",
    )
    register_admin(admin)

    # --- media (Django MEDIA_ROOT) --------------------------------------------
    if settings.MEDIA_DIR.exists():
        app.mount(
            "/media",
            StaticFiles(directory=str(settings.MEDIA_DIR)),
            name="media",
        )

    return app


app = create_app()
