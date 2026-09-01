"""Application-wide base model with a predictable serialization contract."""

from datetime import UTC, datetime
from typing import Any, Self, TypeVar, cast

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class CustomModel(BaseModel):
    """Application-wide base model with a predictable serialization contract."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @model_validator(mode="after")
    def _attach_utc(self) -> Self:
        """Treat naive datetimes as UTC so JSON always carries an offset.

        Deliberately a validator rather than a wildcard ``field_serializer``: a
        serializer annotated ``-> Any`` erases every field's type from the
        OpenAPI serialization schema, leaving the documented response shape
        untyped.
        """
        for name, value in self.__dict__.items():
            if isinstance(value, datetime) and value.tzinfo is None:
                self.__dict__[name] = value.replace(tzinfo=UTC)
        return self

    def serializable_dict(self, **kwargs: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", jsonable_encoder(self.model_dump(**kwargs)))


class ErrorDetail(CustomModel):
    """Structured error detail for envelope responses."""

    code: str
    message: str
    field: str | None = Field(
        default=None,
        description=(
            "Dotted path to the offending input on a validation error, "
            "e.g. ``body.email`` or ``query.page``."
        ),
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Context an error attached via ``AppError(extra=...)``.",
    )


class Pagination(CustomModel):
    """Where a list response sits in the full result set.

    A top-level member rather than part of ``meta``: it describes the payload,
    not the request, and only list responses carry it.
    """

    page: int = Field(examples=[1])
    per_page: int = Field(examples=[20])
    total: int = Field(examples=[245])
    total_pages: int = Field(examples=[13])
    has_next: bool = Field(examples=[True])
    has_previous: bool = Field(examples=[False])


class EnvelopeMeta(CustomModel):
    """Metadata about the request itself, carried by every response."""

    request_id: str = Field(examples=["3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c"])


class Envelope[T](CustomModel):
    """Standard success/error envelope for all API responses."""

    success: bool = Field(examples=[True])
    data: T | None = None
    message: str | None = Field(default=None, examples=["Operation successful"])
    errors: list[ErrorDetail] | None = Field(default=None, examples=[None])
    meta: EnvelopeMeta


class EnvelopeList[T](CustomModel):
    """Standard envelope for paginated list responses."""

    success: bool = Field(examples=[True])
    data: list[T]
    message: str | None = Field(default=None, examples=["Items retrieved"])
    errors: list[ErrorDetail] | None = Field(default=None, examples=[None])
    pagination: Pagination
    meta: EnvelopeMeta
