"""Domain event value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    """An immutable record of something that happened in the domain.

    Use cases return a list of these; the route layer dispatches them to the
    event bus after the use case succeeds, keeping use cases side-effect-free.
    """

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
