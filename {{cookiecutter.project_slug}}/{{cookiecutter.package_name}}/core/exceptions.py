from typing import Any

from .schemas import Envelope, EnvelopeMeta, ErrorDetail


class AppError(Exception):
    """Base domain error, rendered as ``{"code": ..., "message": ...}``."""

    status_code = 500
    code = "internal_error"

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__doc__ or "An unexpected error occurred."
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.extra = extra or {}
        super().__init__(self.message)

    def to_error_detail(self) -> ErrorDetail:
        """Convert to structured error detail for envelope."""
        return ErrorDetail(
            code=self.code,
            message=self.message,
            data=self.extra or None,
        )

    def response_headers(self) -> dict[str, str]:
        """HTTP headers this error must carry (e.g. ``Retry-After``)."""
        return {}

    def to_envelope(
        self, request_id: str, meta: EnvelopeMeta | None = None
    ) -> Envelope[None]:
        """Convert to error envelope response."""
        if meta is None:
            meta = EnvelopeMeta(request_id=request_id)
        return Envelope(
            success=False,
            data=None,
            message=self.message,
            errors=[self.to_error_detail()],
            meta=meta,
        )


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    code = "conflict"


class UnauthorizedError(AppError):
    """Authentication is required or the provided credentials are invalid."""

    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    """The authenticated user lacks permission for this action."""

    status_code = 403
    code = "forbidden"


class BadRequestError(AppError):
    """The request is malformed or its payload is invalid."""

    status_code = 400
    code = "bad_request"


class RateLimitedError(AppError):
    """Too many requests."""

    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str | None = None, *, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            message or "Too many requests, slow down.",
            extra={"retry_after": retry_after},
        )

    def response_headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after)}
