"""Pagination helpers (mirrors Django's Paginator)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import Query
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.sql.selectable import Select

    from .schemas import Pagination


@dataclass
class PageParams:
    page: int = 1
    size: int = 20


async def page_params(
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PageParams:
    return PageParams(page=page, size=size)


@dataclass
class Page[T]:
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, params: PageParams) -> Page[T]:
        size = params.size or 1
        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=(total + size - 1) // size,
        )

    def to_pagination(self) -> Pagination:
        """Describe where this page sits in the full result set."""
        from .schemas import Pagination

        return Pagination(
            page=self.page,
            per_page=self.size,
            total=self.total,
            total_pages=self.pages,
            has_next=self.page < self.pages,
            has_previous=self.page > 1,
        )


def paginate_stmt[T: tuple[Any, ...]](stmt: Select[T], params: PageParams) -> Select[T]:
    """Apply offset/limit to a SELECT statement."""
    return stmt.limit(params.size).offset((params.page - 1) * params.size)


async def count_total(session, stmt):  # type: ignore[no-untyped-def]
    """Return total rows a SELECT would match."""
    count_stmt = select(func.count()).select_from(stmt.subquery())
    return (await session.execute(count_stmt)).scalar_one()
