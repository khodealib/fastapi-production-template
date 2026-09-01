"""Application-wide base model with a predictable serialization contract."""

from datetime import datetime
from typing import Any, TypeVar, cast
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, field_serializer

T = TypeVar("T")


class CustomModel(BaseModel):
    """Application-wide base model with a predictable serialization contract."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=ZoneInfo("UTC"))
            return value.isoformat()
        return value

    def serializable_dict(self, **kwargs: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", jsonable_encoder(self.model_dump(**kwargs)))


class ErrorDetail(CustomModel):
    """Structured error detail for envelope responses."""

    code: str
    message: str
    field: str | None = None


class PaginationMeta(CustomModel):
    """Pagination metadata for envelope responses."""

    page: int
    size: int
    total: int
    pages: int


class EnvelopeMeta(CustomModel):
    """Metadata for envelope responses."""

    request_id: str
    pagination: PaginationMeta | None = None


class Envelope[T](CustomModel):
    """Standard success/error envelope for all API responses."""

    success: bool
    data: T | None = None
    message: str | None = None
    errors: list[ErrorDetail] | None = None
    meta: EnvelopeMeta


class EnvelopeList[T](CustomModel):
    """Standard envelope for paginated list responses."""

    success: bool
    data: list[T]
    message: str | None = None
    errors: list[ErrorDetail] | None = None
    meta: EnvelopeMeta
