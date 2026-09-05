"""Tests for the in-process event bus."""

import logging

import pytest

from app.events import EventBus
from app.modules.users.events import USER_LOGGED_IN, USER_REGISTERED


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
