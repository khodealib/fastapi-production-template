"""OpenAPI documentation helpers.

A route's ``responses`` map is derived from the ``AppError`` subclasses it can
raise, so the documented status codes, error codes, descriptions, examples and
headers cannot drift from the exceptions themselves — the class is the single
source of truth.
"""

from __future__ import annotations

import inspect
from typing import Any

from app.exceptions.errors import AppError

from .schemas import Envelope, ErrorDetail

VALIDATION_STATUS = 422
VALIDATION_CODE = "validation_error"
VALIDATION_DESCRIPTION = "The request failed schema validation."

_EXAMPLE_REQUEST_ID = "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c"

_HEADER_DESCRIPTIONS = {
    "Retry-After": "Seconds to wait before retrying the request.",
}


def describe(error: type[AppError]) -> str:
    """Return an error class's docstring as a one-line OpenAPI description."""
    return inspect.cleandoc(error.__doc__ or "").strip() or "The request failed."


def _default_instance(error: type[AppError]) -> AppError | None:
    """Instantiate the error so examples mirror what a client really receives.

    Subclasses whose constructor demands arguments cannot be sampled this way;
    they fall back to a description-only example.
    """
    try:
        return error()
    except TypeError:
        return None


def _envelope_example(detail: ErrorDetail) -> dict[str, Any]:
    """Render the envelope a client actually receives for this error."""
    return {
        "success": False,
        "data": None,
        "message": detail.message,
        "errors": [detail.model_dump(mode="json")],
        "meta": {"request_id": _EXAMPLE_REQUEST_ID},
    }


def _document_headers(headers: dict[str, str], status_code: int) -> dict[str, Any]:
    return {
        name: {
            "description": _HEADER_DESCRIPTIONS.get(
                name, f"Sent with every {status_code} response."
            ),
            "schema": {"type": "string"},
            "example": value,
        }
        for name, value in headers.items()
    }


def error_responses(
    *errors: type[AppError],
    validation: bool = False,
) -> dict[int | str, dict[str, Any]]:
    """Build an OpenAPI ``responses`` map for the errors a route can raise.

    Pass the exception classes themselves::

        @router.get("/{user_id}", responses=error_responses(ForbiddenError,
                                                            NotFoundError))

    Each example is rendered from a real instance of the class, so a default
    message, the context attached via ``extra`` and any response header — such
    as ``Retry-After`` on a 429 — are documented exactly as they are sent.

    Errors sharing a status code are merged into one entry with an example per
    error code. ``validation=True`` documents the 422 the app really returns —
    FastAPI's built-in 422 schema describes a bare list, not the envelope.
    """
    grouped: dict[int, list[type[AppError]]] = {}
    for error in errors:
        grouped.setdefault(error.status_code, []).append(error)
    if validation:
        grouped.setdefault(VALIDATION_STATUS, [])

    responses: dict[int | str, dict[str, Any]] = {}
    for status_code, group in sorted(grouped.items()):
        descriptions: list[str] = []
        examples: dict[str, Any] = {}
        headers: dict[str, str] = {}

        for error in group:
            descriptions.append(describe(error))
            instance = _default_instance(error)
            if instance is None:
                detail = ErrorDetail(code=error.code, message=describe(error))
            else:
                detail = instance.to_error_detail()
                headers.update(instance.response_headers())
            examples[error.code] = {
                "summary": error.code,
                "value": _envelope_example(detail),
            }

        if validation and status_code == VALIDATION_STATUS:
            descriptions.append(VALIDATION_DESCRIPTION)
            examples[VALIDATION_CODE] = {
                "summary": VALIDATION_CODE,
                "value": _envelope_example(
                    ErrorDetail(code=VALIDATION_CODE, message="Field required")
                ),
            }

        entry: dict[str, Any] = {
            "model": Envelope[None],
            "description": " ".join(descriptions),
            "content": {"application/json": {"examples": examples}},
        }
        if headers:
            entry["headers"] = _document_headers(headers, status_code)
        responses[status_code] = entry

    return responses
