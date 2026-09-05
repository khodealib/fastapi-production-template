"""Tests for the in-process event bus."""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.events import DomainEvent, EventBus, bus, dispatch_events
from app.modules.users.events import USER_LOGGED_IN, USER_REGISTERED
from app.modules.users.repositories import UserRepository
from app.modules.users.usecases import AuthenticateUser, RegisterUser

PASSWORD = "SuperS3cret!"
EMAIL = "collector@example.com"


@pytest.fixture
def recorded() -> Iterator[list[dict[str, Any]]]:
    """Record `users.registered` payloads on the shared bus, then unsubscribe."""
    seen: list[dict[str, Any]] = []

    async def recorder(**kwargs: Any) -> None:
        seen.append(kwargs)

    bus.subscribe(USER_REGISTERED)(recorder)
    yield seen
    bus._handlers[USER_REGISTERED].remove(recorder)


async def test_publish_without_handlers_is_a_no_op() -> None:
    """An event nobody subscribed to is silently dropped."""
    bus = EventBus()
    await bus.publish("nothing.listens", value=1)


async def test_subscribe_returns_the_handler_unchanged() -> None:
    """The decorator registers the handler and hands it back as-is."""
    bus = EventBus()

    async def handler() -> None: ...

    assert bus.subscribe("some.event")(handler) is handler


async def test_publish_fans_out_to_every_handler() -> None:
    """All handlers for an event run, each receiving the published kwargs."""
    bus = EventBus()
    seen: list[tuple[str, str]] = []

    @bus.subscribe("thing.happened")
    async def first(name: str) -> None:
        seen.append(("first", name))

    @bus.subscribe("thing.happened")
    async def second(name: str) -> None:
        seen.append(("second", name))

    await bus.publish("thing.happened", name="widget")

    assert sorted(seen) == [("first", "widget"), ("second", "widget")]


async def test_handlers_are_isolated_per_event() -> None:
    """Publishing one event does not run another event's handlers."""
    bus = EventBus()
    calls: list[str] = []

    @bus.subscribe("a.happened")
    async def on_a() -> None:
        calls.append("a")

    @bus.subscribe("b.happened")
    async def on_b() -> None:
        calls.append("b")

    await bus.publish("a.happened")

    assert calls == ["a"]


async def test_a_failing_handler_is_logged_and_does_not_stop_the_others(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One raising handler neither blocks its peers nor fails the publisher."""
    bus = EventBus()
    survived: list[str] = []

    @bus.subscribe("risky.happened")
    async def boom() -> None:
        raise RuntimeError("handler exploded")

    @bus.subscribe("risky.happened")
    async def fine() -> None:
        survived.append("fine")

    with caplog.at_level(logging.ERROR, logger="app.events.bus"):
        await bus.publish("risky.happened")

    assert survived == ["fine"]
    assert "handler exploded" in caplog.text


async def test_users_module_handlers_are_registered(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Importing the app wires the users module's handlers onto the shared bus."""
    from app.events import bus

    with caplog.at_level(logging.INFO, logger="app.modules.users.events.handlers"):
        await bus.publish(USER_REGISTERED, user_id="u-1", email="a@example.com")
        await bus.publish(USER_LOGGED_IN, user_id="u-1")

    assert "User registered" in caplog.text
    assert "User logged in" in caplog.text


async def test_dispatch_events_publishes_each_collected_event(
    recorded: list[dict[str, Any]],
) -> None:
    """`dispatch_events` fans a collected list out to the shared bus in order."""
    await dispatch_events(
        [
            DomainEvent(USER_REGISTERED, {"user_id": "u-1", "email": "a@example.com"}),
            DomainEvent(USER_REGISTERED, {"user_id": "u-2", "email": "b@example.com"}),
        ]
    )

    assert [payload["user_id"] for payload in recorded] == ["u-1", "u-2"]


async def test_dispatch_events_with_no_events_is_a_no_op(
    recorded: list[dict[str, Any]],
) -> None:
    """A use case that collected nothing publishes nothing."""
    await dispatch_events([])

    assert recorded == []


async def test_register_user_collects_instead_of_publishing(
    session_factory: async_sessionmaker[AsyncSession],
    recorded: list[dict[str, Any]],
) -> None:
    """The use case returns the event and leaves publishing to its caller."""
    async with session_factory() as session:
        user, events = await RegisterUser(UserRepository(session)).execute(
            email=EMAIL, password=PASSWORD, full_name="Collector"
        )

    assert recorded == []
    assert events == [
        DomainEvent(USER_REGISTERED, {"user_id": str(user.id), "email": user.email})
    ]

    await dispatch_events(events)

    assert recorded == [{"user_id": str(user.id), "email": user.email}]


async def test_authenticate_user_collects_instead_of_publishing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Authentication is side-effect-free too: the login event is returned."""
    async with session_factory() as session:
        repo = UserRepository(session)
        registered, _ = await RegisterUser(repo).execute(
            email=EMAIL, password=PASSWORD, full_name="Collector"
        )
        user, events = await AuthenticateUser(repo).execute(
            email=EMAIL, password=PASSWORD
        )

    assert user.id == registered.id
    assert events == [DomainEvent(USER_LOGGED_IN, {"user_id": str(user.id)})]


async def test_register_route_dispatches_the_collected_events(
    client: AsyncClient,
    recorded: list[dict[str, Any]],
) -> None:
    """The route is the layer that publishes, so the handler still fires."""
    resp = await client.post(
        "/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Collector"},
    )

    assert resp.status_code == 201
    assert recorded == [{"user_id": resp.json()["data"]["id"], "email": EMAIL}]
