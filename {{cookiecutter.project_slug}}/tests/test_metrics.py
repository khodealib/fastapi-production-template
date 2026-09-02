"""Tests for the Prometheus metrics endpoint."""

from httpx import AsyncClient


async def test_metrics_returns_200(client: AsyncClient) -> None:
    """The scrape endpoint answers in Prometheus text format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


async def test_metrics_absent_from_openapi(client: AsyncClient) -> None:
    """It is an operational endpoint, deliberately kept out of the schema."""
    openapi = (await client.get("/openapi.json")).json()
    assert "/metrics" not in openapi["paths"]
