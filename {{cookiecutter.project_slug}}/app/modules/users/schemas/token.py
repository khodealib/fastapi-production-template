"""API-boundary schemas for the token pair."""

from __future__ import annotations

from uuid import UUID

from app.http.schemas import CustomModel, Envelope


class TokenResponse(CustomModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(CustomModel):
    refresh_token: str


class TokenData(CustomModel):
    sub: UUID
    type: str


# Envelope type aliases for response_model
TokenResponseEnvelope = Envelope[TokenResponse]
