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
        return ErrorDetail(code=self.code, message=self.message)

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
    status_code = 404
    code = "not_found"
    """The requested resource does not exist."""


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    """The request conflicts with the current state of the resource."""


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    """Authentication is required or the provided credentials are invalid."""


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    """The authenticated user lacks permission for this action."""


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    """The request is malformed or its payload is invalid."""


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    """Too many requests."""

    def __init__(self, message: str | None = None, *, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            message or "Too many requests, slow down.",
            extra={"retry_after": retry_after},
        )
