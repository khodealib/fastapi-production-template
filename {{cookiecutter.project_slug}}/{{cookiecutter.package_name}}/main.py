"""Application factory + root wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from .api import api_router
from .core.admin_auth import AdminAuth
from .core.config import get_settings
from .core.constants import Environment
from .core.database import dispose_engine, engine
from .core.exception_handlers import register_exception_handlers
from .core.health import health_router
from .core.logging_conf import configure_logging
from .infrastructure.cache import close_redis
from .middleware import (
    RateLimitHeadersMiddleware,
    RequestContextMiddleware,
)
from .modules.users.admin import register_admin

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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
    register_exception_handlers(app)

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
