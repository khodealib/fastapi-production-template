---
name: pydantic-schema
description: Write Pydantic API-boundary schemas on CustomModel: Create/Read/Update/Detail shapes, field validation, and the Envelope[T] / EnvelopeList[T] aliases a route uses as its response_model. Use when adding or changing request or response schemas.
---

# pydantic-schema

Generate Pydantic schemas for API boundaries.

## Instructions

1. Create or update `modules/{module}/schemas/{resource}.py` with:
   - `from __future__ import annotations`
   - Import from `pydantic`
   - Import `CustomModel` from `app.http.schemas`
   - Re-export the schemas from `modules/{module}/schemas/__init__.py`

2. Base schema pattern:
   ```python
   from datetime import datetime
   from uuid import UUID

   from pydantic import EmailStr, Field, field_validator

   from app.http.schemas import CustomModel
   ```

3. Create schema:
   ```python
   class {Model}Create(CustomModel):
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
   ```

4. Read schema:
   ```python
   class {Model}Read(CustomModel):
       id: UUID
       email: EmailStr
       full_name: str | None
       is_active: bool
       created_at: datetime
   ```

5. Update schema (partial updates):
   ```python
   class {Model}Update(CustomModel):
       full_name: str | None = Field(default=None, max_length=255)
       email: EmailStr | None = None
   ```

6. Nested response schema:
   ```python
   class {Model}Detail(CustomModel):
       id: UUID
       email: EmailStr
       items: list[{Item}Read] = []
   ```

7. Token/auth schemas:
   ```python
   class TokenResponse(CustomModel):
       access_token: str
       refresh_token: str
       token_type: str = "bearer"
       expires_in: int


   class RefreshRequest(CustomModel):
       refresh_token: str
   ```

## Conventions

- All schemas inherit from `CustomModel` (has datetime serialization, `from_attributes`)
- Read schemas use `model_validate(orm_object)` with `from_attributes=True`
- Use `EmailStr` for email fields
- Use `Field()` for validation (min_length, max_length, ge, le)
- Passwords: min 8 chars, require complexity (use `STRONG_PASSWORD_RE`)
- UUIDs for primary keys
- Datetime fields use ISO format (handled by `CustomModel`)
- Optional fields: `str | None = None`
- No business logic in schemas (validation only)
