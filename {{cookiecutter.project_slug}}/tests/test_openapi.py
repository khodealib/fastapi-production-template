"""Tests for the OpenAPI error documentation helpers."""

from typing import Any

from httpx import AsyncClient

from {{ cookiecutter.package_name }}.core.config import get_settings
from {{ cookiecutter.package_name }}.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
)
from {{ cookiecutter.package_name }}.core.openapi import describe, error_responses


def test_error_class_docstrings_are_real_docstrings() -> None:
    """Each AppError subclass must carry its default message as a docstring.

    A string literal placed after the class attributes is not a docstring, so
    __doc__ would be None and `raise NotFoundError()` would fall back to the
    generic AppError message.
    """
    for error in (NotFoundError, ConflictError, ForbiddenError, RateLimitedError):
        assert error.__doc__, f"{error.__name__} has no docstring"

    # Subclasses that do not override __init__ default their message to it.
    for error in (NotFoundError, ConflictError, ForbiddenError):
        assert error().message == describe(error)


def test_error_responses_keys_by_status_code() -> None:
    responses = error_responses(ForbiddenError, NotFoundError)
    assert sorted(responses) == [403, 404]
    assert responses[404]["description"] == NotFoundError.__doc__


def test_error_responses_merges_shared_status_codes() -> None:
    class OtherNotFound(AppError):
        """The other thing is missing."""

        status_code = 404
        code = "other_not_found"

    responses = error_responses(NotFoundError, OtherNotFound)
    assert sorted(responses) == [404]
    examples = responses[404]["content"]["application/json"]["examples"]
    assert sorted(examples) == ["not_found", "other_not_found"]


def test_error_responses_documents_the_envelope_shaped_422() -> None:
    responses = error_responses(NotFoundError, validation=True)
    assert 422 in responses
    examples = responses[422]["content"]["application/json"]["examples"]
    detail = examples["validation_error"]["value"]["errors"][0]
    assert detail["code"] == "validation_error"
    # The same example is reused on routes with no body, so it names no field.
    assert detail["field"] is None


async def test_openapi_documents_error_statuses(client: AsyncClient) -> None:
    """The generated schema advertises the errors each route can raise."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths: dict[str, Any] = resp.json()["paths"]

    detail = paths["/api/users/{user_id}"]["get"]["responses"]
    # 429 arrives from the api_router's global limiter.
    assert sorted(detail) == ["200", "401", "403", "404", "422", "429"]

    schema = detail["404"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("Envelope_NoneType_")


async def test_openapi_documents_probe_unavailability(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    paths: dict[str, Any] = resp.json()["paths"]
    assert "503" in paths["/ready"]["get"]["responses"]
    assert "503" in paths["/health"]["get"]["responses"]


async def test_success_response_documents_absent_error_fields(
    client: AsyncClient,
) -> None:
    """A 200 example must not invent an error object, nor carry pagination."""
    resp = await client.get("/openapi.json")
    schemas = resp.json()["components"]["schemas"]

    envelope = schemas["Envelope_UserRead_"]
    assert envelope["properties"]["errors"]["examples"] == [None]
    assert "pagination" not in envelope["properties"]
    assert list(schemas["EnvelopeMeta"]["properties"]) == ["request_id"]


async def test_list_response_documents_pagination_at_the_root(
    client: AsyncClient,
) -> None:
    """Pagination is a top-level member of a list response, not metadata."""
    resp = await client.get("/openapi.json")
    schemas = resp.json()["components"]["schemas"]

    envelope = schemas["EnvelopeList_UserRead_"]
    assert "pagination" in envelope["required"]
    assert envelope["properties"]["pagination"]["$ref"].endswith("Pagination")

    assert sorted(schemas["Pagination"]["properties"]) == [
        "has_next",
        "has_previous",
        "page",
        "page_size",
        "total",
        "total_pages",
    ]


async def test_openapi_title_comes_from_settings(client: AsyncClient) -> None:
    """The generated project names itself, rather than the template fixture."""
    resp = await client.get("/openapi.json")
    info = resp.json()["info"]

    assert info["title"] == get_settings().APP_NAME
    assert "Fixture" not in info["title"]
    assert "Fixture" not in info["description"]


def test_rate_limit_example_matches_a_real_response() -> None:
    """The 429 example is rendered from an actual RateLimitedError instance."""
    responses = error_responses(RateLimitedError)
    example = responses[429]["content"]["application/json"]["examples"]
    detail = example["rate_limited"]["value"]["errors"][0]

    assert detail["code"] == "rate_limited"
    assert detail["message"] == RateLimitedError().message
    assert detail["data"] == {"retry_after": RateLimitedError().retry_after}


def test_rate_limit_response_documents_the_retry_after_header() -> None:
    headers = error_responses(RateLimitedError)[429]["headers"]
    assert "Retry-After" in headers
    assert headers["Retry-After"]["schema"]["type"] == "string"


def test_errors_without_a_default_constructor_still_document() -> None:
    class NeedsArgs(AppError):
        """This one cannot be sampled."""

        status_code = 418
        code = "needs_args"

        def __init__(self, required: str) -> None:
            super().__init__(required)

    responses = error_responses(NeedsArgs)
    detail = responses[418]["content"]["application/json"]["examples"]["needs_args"]
    assert detail["value"]["errors"][0]["message"] == "This one cannot be sampled."


async def test_openapi_documents_the_rate_limit_header(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    limited = resp.json()["paths"]["/api/auth/token"]["post"]["responses"]["429"]

    assert "Retry-After" in limited["headers"]
    example = limited["content"]["application/json"]["examples"]["rate_limited"]
    assert example["value"]["errors"][0]["data"]["retry_after"] > 0
