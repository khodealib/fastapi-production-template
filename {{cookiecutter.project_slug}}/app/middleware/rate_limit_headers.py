"""Emit X-RateLimit-* headers stashed by the rate_limit dependency."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Emit X-RateLimit-* headers stashed by the ``rate_limit`` dependency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        meta = getattr(request.state, "rate_limit", None)
        if meta:
            response.headers["X-RateLimit-Limit"] = str(meta["limit"])
            response.headers["X-RateLimit-Remaining"] = str(meta["remaining"])
            response.headers["X-RateLimit-Reset"] = str(meta["reset"])
        return response
