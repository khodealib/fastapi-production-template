"""Tests for the layered rate limiter."""

from collections.abc import AsyncIterator, Callable
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from {{ cookiecutter.package_name }}.core.exception_handlers import (
    register_exception_handlers,
)
from {{ cookiecutter.package_name }}.core.net import UNKNOWN_CLIENT, resolve_client_ip
from {{ cookiecutter.package_name }}.infrastructure.ratelimit import (
    RateLimitStrategy,
    rate_limit,
)
from {{ cookiecutter.package_name }}.middleware import RateLimitHeadersMiddleware


def _build_app(*dependencies: Callable[..., Any]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitHeadersMiddleware)
    register_exception_handlers(app)
    router = APIRouter(dependencies=[Depends(d) for d in dependencies])

    @router.get("/first")
    async def first() -> dict[str, bool]:
        return {"ok": True}

    @router.get("/second")
    async def second() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(router)
    return app


@pytest.fixture
async def limited_client() -> AsyncIterator[AsyncClient]:
    """Two endpoints sharing one app-wide budget of two requests."""
    app = _build_app(rate_limit("2/minute", key_prefix="shared", per_path=False))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_global_budget_is_shared_across_routes(
    limited_client: AsyncClient,
) -> None:
    """With per_path=False, hits on one route count against the other."""
    assert (await limited_client.get("/first")).status_code == 200
    assert (await limited_client.get("/second")).status_code == 200

    blocked = await limited_client.get("/first")

    assert blocked.status_code == 429
    assert blocked.json()["errors"][0]["code"] == "rate_limited"


async def test_per_path_budgets_are_independent() -> None:
    """The default keeps a separate counter for each route."""
    app = _build_app(rate_limit("1/minute", key_prefix="per_path"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.get("/first")).status_code == 200
        assert (await ac.get("/second")).status_code == 200
        assert (await ac.get("/first")).status_code == 429


async def test_a_route_can_choose_its_own_strategy() -> None:
    """A stricter algorithm can be picked per dependency."""
    app = _build_app(
        rate_limit(
            "1/minute",
            strategy=RateLimitStrategy.MOVING_WINDOW,
            key_prefix="moving",
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.get("/first")).status_code == 200
        assert (await ac.get("/first")).status_code == 429


async def test_narrower_route_limit_owns_the_headers() -> None:
    """Router limit runs first, so the route's own limit reports the headers."""
    app = _build_app(
        rate_limit("100/minute", key_prefix="wide", per_path=False),
        rate_limit("10/minute", key_prefix="narrow"),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/first")

    assert resp.headers["X-RateLimit-Limit"] == "10"


async def test_every_api_route_documents_the_rate_limit(client: AsyncClient) -> None:
    """The global limiter applies under API_PREFIX, so 429 belongs everywhere."""
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]

    api_routes = [p for p in paths if p.startswith("/api")]
    assert api_routes
    for path in api_routes:
        for method, op in paths[path].items():
            assert "429" in op["responses"], f"{method.upper()} {path} omits 429"


async def test_probes_are_not_rate_limited(client: AsyncClient) -> None:
    """Health probes sit outside API_PREFIX and must stay unthrottled."""
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]

    for probe in ("/live", "/ready", "/health"):
        assert "429" not in paths[probe]["get"]["responses"]


class _FakeRequest:
    """Minimal stand-in — resolve_client_ip only reads headers and client."""

    def __init__(self, peer: str | None, forwarded: str | None = None) -> None:
        self.headers = {"X-Forwarded-For": forwarded} if forwarded else {}
        self.client = SimpleNamespace(host=peer) if peer else None


def test_forwarded_for_is_ignored_without_trusted_proxies() -> None:
    """The default must not let a client name its own address."""
    request = _FakeRequest("10.0.0.1", forwarded="1.2.3.4")
    assert resolve_client_ip(request, 0) == "10.0.0.1"


def test_one_proxy_uses_the_address_that_proxy_appended() -> None:
    """Behind one proxy the rightmost entry is the only trustworthy one."""
    request = _FakeRequest("10.0.0.1", forwarded="9.9.9.9, 203.0.113.7")
    assert resolve_client_ip(request, 1) == "203.0.113.7"


def test_two_proxies_step_further_back_along_the_chain() -> None:
    request = _FakeRequest("10.0.0.1", forwarded="9.9.9.9, 203.0.113.7, 10.0.0.9")
    assert resolve_client_ip(request, 2) == "203.0.113.7"


def test_short_or_missing_chain_falls_back_to_the_peer() -> None:
    assert resolve_client_ip(_FakeRequest("10.0.0.1"), 1) == "10.0.0.1"
    short = _FakeRequest("10.0.0.1", forwarded="203.0.113.7")
    assert resolve_client_ip(short, 2) == "10.0.0.1"
    assert resolve_client_ip(_FakeRequest(None), 0) == UNKNOWN_CLIENT


async def test_forwarded_clients_get_separate_budgets() -> None:
    """Two callers behind one proxy must not share a bucket."""
    app = _build_app(
        rate_limit(
            "1/minute",
            scope=lambda request: resolve_client_ip(request, 1),
            key_prefix="forwarded",
            per_path=False,
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        alice = {"X-Forwarded-For": "203.0.113.7"}
        bob = {"X-Forwarded-For": "203.0.113.8"}

        assert (await ac.get("/first", headers=alice)).status_code == 200
        assert (await ac.get("/first", headers=bob)).status_code == 200
        assert (await ac.get("/second", headers=alice)).status_code == 429
