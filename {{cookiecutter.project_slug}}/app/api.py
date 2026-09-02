"""Root API router: mounts all module routers."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config.settings import get_settings
from app.exceptions.errors import RateLimitedError
from app.http.openapi import error_responses
from app.infrastructure.ratelimit import rate_limit
from app.modules.users.routes import auth_router, users_router

_settings = get_settings()

# Applies to every API route, as one budget per client rather than
# per endpoint. A route needing something stricter — or a different algorithm —
# declares its own `rate_limit(...)`, which runs after this one and therefore
# owns the X-RateLimit-* headers.
global_rate_limit = rate_limit(
    _settings.RATE_LIMIT_GLOBAL,
    key_prefix="global",
    per_path=False,
)

api_router = APIRouter(
    dependencies=[Depends(global_rate_limit)],
    responses=error_responses(RateLimitedError),
)
api_router.include_router(auth_router)
api_router.include_router(users_router)
