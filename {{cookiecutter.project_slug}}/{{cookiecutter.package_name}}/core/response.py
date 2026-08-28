"""Response envelope helpers for consistent API responses."""

from __future__ import annotations

from typing import TypeVar

from fastapi import Request

from .pagination import Page, PageParams
from .schemas import Envelope, EnvelopeList, EnvelopeMeta, ErrorDetail

T = TypeVar("T")


def _get_request_id(request: Request | None) -> str:
    """Extract request_id from request state."""
    if request and hasattr(request.state, "request_id"):
        return request.state.request_id  # type: ignore[no-any-return]
    return "unknown"


def success_response[T](
    data: T,
    message: str | None = None,
    request: Request | None = None,
    meta: EnvelopeMeta | None = None,
) -> Envelope[T]:
    """Create a success envelope response."""
    request_id = _get_request_id(request)
    if meta is None:
        meta = EnvelopeMeta(request_id=request_id)
    elif meta.request_id == "unknown" and request:
        meta.request_id = _get_request_id(request)
    return Envelope(
        success=True,
        data=data,
        message=message,
        errors=None,
        meta=meta,
    )


def error_response(
    exc: Exception,
    request: Request | None = None,
    meta: EnvelopeMeta | None = None,
) -> Envelope[None]:
    """Create an error envelope response from an AppError."""
    from .exceptions import AppError

    request_id = _get_request_id(request)
    if meta is None:
        meta = EnvelopeMeta(request_id=request_id)
    elif meta.request_id == "unknown" and request:
        meta.request_id = _get_request_id(request)

    if isinstance(exc, AppError):
        return exc.to_envelope(request_id, meta)

    # Generic fallback for unexpected errors
    return Envelope(
        success=False,
        data=None,
        message=str(exc) or "An unexpected error occurred.",
        errors=[ErrorDetail(code="internal_error", message=str(exc))],
        meta=meta,
    )


def validation_error_response(
    errors: list[ErrorDetail],
    message: str = "Validation failed",
    request: Request | None = None,
    meta: EnvelopeMeta | None = None,
) -> Envelope[None]:
    """Create a validation error envelope response (HTTP 422)."""
    request_id = _get_request_id(request)
    if meta is None:
        meta = EnvelopeMeta(request_id=request_id)
    elif meta.request_id == "unknown" and request:
        meta.request_id = _get_request_id(request)
    return Envelope(
        success=False,
        data=None,
        message=message,
        errors=errors,
        meta=meta,
    )


def paginated_response[T](
    items: list[T],
    total: int,
    params: PageParams,
    message: str | None = None,
    request: Request | None = None,
) -> EnvelopeList[T]:
    """Create a paginated list envelope response."""
    request_id = _get_request_id(request)
    page_obj = Page.build(items, total, params)
    meta = page_obj.to_envelope_meta(request_id)
    return EnvelopeList(
        success=True,
        data=items,
        message=message,
        errors=None,
        meta=meta,
    )
