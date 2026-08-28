import pytest
from httpx import AsyncClient
from {{ cookiecutter.package_name }}.core.config import Settings
from {{ cookiecutter.package_name }}.core.constants import Environment


async def test_live(client: AsyncClient) -> None:
    resp = await client.get("/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "version" in body


def test_production_settings_reject_dev_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        Settings(ENVIRONMENT=Environment.PRODUCTION)
    secure = Settings(ENVIRONMENT=Environment.PRODUCTION, SECRET_KEY="a-real-secret")
    assert secure.is_production is True