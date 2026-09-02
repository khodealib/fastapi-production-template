---
name: sqlalchemy-model
description: Write a SQLAlchemy 2.0 ORM entity: Mapped[] annotations, UUID primary key, created_at/updated_at, relationships with cascades, module-level query helpers, and the alembic/env.py import. Use when adding or changing a database entity.
---

# sqlalchemy-model

Generate a new SQLAlchemy ORM model.

## Instructions

1. Create `modules/{module}/models/{entity}.py` — one entity per file — with:
   - `from __future__ import annotations`
   - Import from `sqlalchemy` and `sqlalchemy.orm`
   - Import `Base` from `app.database.base`
   - Import `utcnow` from `app.utils.datetime` — never redefine it locally
   - Re-export the entity from `modules/{module}/models/__init__.py`

2. Model pattern:
   ```python
   from datetime import datetime
   from uuid import UUID, uuid4

   from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func, select
   from sqlalchemy.orm import Mapped, mapped_column, relationship

   from app.database.base import Base
   from app.utils.datetime import utcnow


   class {Model}(Base):
       __tablename__ = "{table_name}"

       id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
       # ... fields ...
       created_at: Mapped[datetime] = mapped_column(
           DateTime(timezone=True), default=utcnow, server_default=func.now()
       )
       updated_at: Mapped[datetime] = mapped_column(
           DateTime(timezone=True),
           default=utcnow,
           server_default=func.now(),
           onupdate=utcnow,
       )
   ```

3. For relationships:
   ```python
   from sqlalchemy.orm import Mapped, mapped_column, relationship

   class Parent(Base):
       children: Mapped[list[Child]] = relationship(
           back_populates="parent", cascade="all, delete-orphan"
       )

   class Child(Base):
       parent_id: Mapped[UUID] = mapped_column(
           Uuid, ForeignKey("parents.id", ondelete="CASCADE"), index=True
       )
       parent: Mapped[Parent] = relationship(back_populates="children")
   ```

4. Add query helpers at module level:
   ```python
   def stmt_by_email(email: str) -> Select[tuple[User]]:
       return select(User).where(func.lower(User.email) == email.lower())
   ```

5. Register each entity in `alembic/env.py` so autogenerate sees the table:
   ```python
   from app.modules.{module}.models import {Model} as _{Model}  # noqa: F401
   ```

## Conventions

- Table names: plural, snake_case (e.g., `users`, `refresh_tokens`)
- Primary keys: `UUID` with `uuid4` default
- Timestamps: `created_at` and `updated_at` on all models
- Use `Mapped[]` type annotations (SQLAlchemy 2.0 style)
- Foreign keys use `ondelete="CASCADE"` where appropriate
- Index foreign key columns
- Query helpers live at module level, not in the model class
- One entity per file; a relationship to an entity in a sibling file imports it
  under `TYPE_CHECKING` and names it as a string in `Mapped[...]`
