import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind request_id / client_ip to log context + emit a request log line."""

    async def dispatch(  # type: ignore[no-untyped-def]
        self, request: Request, call_next
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        start = time.perf_counter()

        # Store request_id in request.state for access by response builders
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_ip=request.client.host if request.client else "unknown",
            path=request.url.path,
            method=request.method,
        )

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request",
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Emit X-RateLimit-* headers stashed by the ``rate_limit`` dependency."""

    async def dispatch(  # type: ignore[no-untyped-def]
        self, request: Request, call_next
    ) -> Response:
        response: Response = await call_next(request)
        meta = getattr(request.state, "rate_limit", None)
        if meta:
            response.headers["X-RateLimit-Limit"] = str(meta["limit"])
            response.headers["X-RateLimit-Remaining"] = str(meta["remaining"])
            response.headers["X-RateLimit-Reset"] = str(meta["reset"])
        return response
