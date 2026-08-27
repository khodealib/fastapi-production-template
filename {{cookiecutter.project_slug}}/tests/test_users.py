from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from {{ cookiecutter.package_name }}.modules.users.crud import UserRepository
from {{ cookiecutter.package_name }}.modules.users.service import RegisterUser

PASSWORD = "SuperS3cret!"
EMAIL = "alice@example.com"

Payload = dict[str, Any]


def _register_payload(**overrides: str | None) -> Payload:
    payload: Payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Alice Example",
    }
    payload.update(overrides)
    return payload


async def _register(client: AsyncClient, email: str = EMAIL) -> Payload:
    resp = await client.post("/api/auth/register", json=_register_payload(email=email))
    assert resp.status_code == 201
    return Payload(resp.json())


async def _login(
    client: AsyncClient, email: str = EMAIL, password: str = PASSWORD
) -> Payload:
    resp = await client.post(
        "/api/auth/token",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200
    return Payload(resp.json())


async def _create_superuser(
    session_factory: async_sessionmaker[AsyncSession],
    password: str = PASSWORD,
) -> None:
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user = await RegisterUser(user_repo).execute(
            email="admin@example.com", password=password, full_name="Admin"
        )
        user.is_superuser = True
        await session.commit()


# --- register ----------------------------------------------------------------


async def test_register_creates_user(client: AsyncClient) -> None:
    user = await _register(client)
    assert user["email"] == EMAIL
    assert user["full_name"] == "Alice Example"
    assert "hashed_password" not in user


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post("/api/auth/register", json=_register_payload())
    assert resp.status_code == 409
    assert resp.json()["code"] == "conflict"


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register", json=_register_payload(password="weakpassword")
    )
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["loc"] == ["body", "password"]


# --- token flow --------------------------------------------------------------


async def test_login_returns_token_pair(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        "/api/auth/token",
        data={"username": EMAIL, "password": "WrongPass1!"},
    )
    assert resp.status_code == 401


async def test_me_requires_and_returns_user(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.get("/api/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == EMAIL

    anon = await client.get("/api/users/me")
    assert anon.status_code == 401


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)

    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Old (revoked) refresh token must be rejected on reuse.
    reuse = await client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401


async def test_refresh_rejects_garbage(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401


# --- admin-only endpoints ----------------------------------------------------


async def test_users_list_requires_superuser(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _register(client)
    await _create_superuser(session_factory)

    # Plain user: forbidden.
    tokens = await _login(client)
    resp = await client.get(
        "/api/users", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 403

    # Superuser: allowed.
    admin = await _login(client, email="admin@example.com")
    resp = await client.get(
        "/api/users", headers={"Authorization": f"Bearer {admin['access_token']}"}
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


async def test_admin_login_page_served(client: AsyncClient) -> None:
    resp = await client.get("/admin")
    assert resp.status_code in (200, 307)
