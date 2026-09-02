"""UTC datetime utilities."""

from datetime import UTC, datetime

__all__ = ["UTC", "utcnow"]


def utcnow() -> datetime:
    return datetime.now(UTC)
