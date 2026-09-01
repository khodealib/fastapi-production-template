"""OpenAPI documentation helpers.

A route's ``responses`` map is derived from the ``AppError`` subclasses it can
raise, so the documented status codes, error codes and descriptions cannot
drift from the exceptions themselves — the class is the single source of truth.
"""

from __future__ import annotations

import inspect
from typing import Any

from .exceptions import AppError
from .schemas import Envelope

VALIDATION_STATUS = 422
VALIDATION_CODE = "validation_error"
VALIDATION_DESCRIPTION = "The request failed schema validation."

_EXAMPLE_REQUEST_ID = "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c"


def describe(error: type[AppError]) -> str:
    """Return an error class's docstring as a one-line OpenAPI description."""
    return inspect.cleandoc(error.__doc__ or "").strip() or "The request failed."


def _example(code: str, message: str, field: str | None = None) -> dict[str, Any]:
    """Render the envelope a client actually receives for this error."""
    return {
        "success": False,
        "data": None,
        "message": message,
        "errors": [{"code": code, "message": message, "field": field}],
        "meta": {"request_id": _EXAMPLE_REQUEST_ID, "pagination": None},
    }


def error_responses(
    *errors: type[AppError],
    validation: bool = False,
) -> dict[int | str, dict[str, Any]]:
    """Build an OpenAPI ``responses`` map for the errors a route can raise.

    Pass the exception classes themselves::

        @router.get("/{user_id}", responses=error_responses(ForbiddenError,
                                                            NotFoundError))

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
        descriptions = [describe(error) for error in group]
        examples = {
            error.code: {"summary": error.code, "value": _example(error.code, text)}
            for error, text in zip(group, descriptions, strict=True)
        }
        if validation and status_code == VALIDATION_STATUS:
            descriptions.append(VALIDATION_DESCRIPTION)
            examples[VALIDATION_CODE] = {
                "summary": VALIDATION_CODE,
                "value": _example(VALIDATION_CODE, "Field required"),
            }
        responses[status_code] = {
            "model": Envelope[None],
            "description": " ".join(descriptions),
            "content": {"application/json": {"examples": examples}},
        }
    return responses
