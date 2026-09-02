"""API-boundary schemas for the user resource. Entities never cross the wire."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.http.schemas import CustomModel, Envelope, EnvelopeList

STRONG_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).+$")


class UserCreate(CustomModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        if not STRONG_PASSWORD_RE.match(value):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit and a symbol."
            )
        return value


class UserRead(CustomModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime


# Envelope type aliases for response_model
UserReadEnvelope = Envelope[UserRead]
UserListEnvelope = EnvelopeList[UserRead]
