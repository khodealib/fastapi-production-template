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
    assert sorted(detail) == ["200", "401", "403", "404", "422"]

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
    """A 200 example must not invent an error object or pagination block."""
    resp = await client.get("/openapi.json")
    schemas = resp.json()["components"]["schemas"]

    assert schemas["Envelope_UserRead_"]["properties"]["errors"]["examples"] == [None]
    assert schemas["EnvelopeMeta"]["properties"]["pagination"]["examples"] == [None]


async def test_list_response_always_documents_pagination(client: AsyncClient) -> None:
    """A list envelope always carries pagination, so it is required there."""
    resp = await client.get("/openapi.json")
    schemas = resp.json()["components"]["schemas"]

    meta = schemas["EnvelopeList_UserRead_"]["properties"]["meta"]
    assert meta["$ref"].endswith("PaginatedMeta")
    assert "pagination" in schemas["PaginatedMeta"]["required"]


async def test_openapi_title_comes_from_settings(client: AsyncClient) -> None:
    """The generated project names itself, rather than the template fixture."""
    resp = await client.get("/openapi.json")
    info = resp.json()["info"]

    assert info["title"] == get_settings().APP_NAME
    assert "Fixture" not in info["title"]
    assert "Fixture" not in info["description"]
