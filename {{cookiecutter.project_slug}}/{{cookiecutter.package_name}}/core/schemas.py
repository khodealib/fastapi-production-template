from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, field_serializer


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


class Message(CustomModel):
    code: str
    message: str
