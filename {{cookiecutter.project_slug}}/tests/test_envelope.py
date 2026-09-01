"""Tests for the response envelope contract."""

from datetime import UTC, datetime

from httpx import AsyncClient

from {{ cookiecutter.package_name }}.core.exceptions import (
    NotFoundError,
    RateLimitedError,
)
from {{ cookiecutter.package_name }}.core.schemas import CustomModel


def test_app_error_extra_reaches_the_error_detail() -> None:
    """`AppError(extra=...)` must survive into the rendered envelope."""
    error = NotFoundError("Gone.", extra={"user_id": "abc"})
    assert error.to_error_detail().data == {"user_id": "abc"}


def test_app_error_without_extra_omits_the_data_field() -> None:
    assert NotFoundError("Gone.").to_error_detail().data is None


def test_rate_limited_error_carries_retry_after() -> None:
    error = RateLimitedError(retry_after=30)
    assert error.response_headers() == {"Retry-After": "30"}
    assert error.to_error_detail().data == {"retry_after": 30}


def test_naive_datetimes_serialize_as_utc() -> None:
    class Model(CustomModel):
        when: datetime

    naive = Model(when=datetime(2026, 9, 1, 12, 30))
    assert naive.when.tzinfo is UTC
    assert naive.model_dump_json() == '{"when":"2026-09-01T12:30:00Z"}'

    aware = Model(when=datetime(2026, 9, 1, 12, 30, tzinfo=UTC))
    assert aware.model_dump_json() == '{"when":"2026-09-01T12:30:00Z"}'


async def test_response_schema_keeps_field_types(client: AsyncClient) -> None:
    """A wildcard field_serializer would erase these from the schema."""
    resp = await client.get("/openapi.json")
    schemas = resp.json()["components"]["schemas"]

    envelope = schemas["Envelope_UserRead_"]["properties"]
    assert envelope["success"]["type"] == "boolean"
    assert envelope["data"]["anyOf"][0]["$ref"].endswith("UserRead")

    user = schemas["UserRead"]["properties"]
    assert user["is_active"]["type"] == "boolean"
    assert user["created_at"]["type"] == "string"
    assert user["created_at"]["format"] == "date-time"


async def test_rate_limited_response_sets_retry_after_header(
    client: AsyncClient,
) -> None:
    """The login limiter allows 5/minute; the sixth call must back off."""
    payload = {"username": "nobody@example.com", "password": "whatever"}
    for _ in range(5):
        await client.post("/api/auth/token", data=payload)

    resp = await client.post("/api/auth/token", data=payload)

    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0
    body = resp.json()
    assert body["errors"][0]["code"] == "rate_limited"
    assert body["errors"][0]["data"]["retry_after"] > 0
