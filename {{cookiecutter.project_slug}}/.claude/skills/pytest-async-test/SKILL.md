---
name: pytest-async-test
description: Write async pytest tests for routes and use cases: the client and session_factory fixtures, register/login helpers, success and error paths, and the 401/403 auth cases. Use when adding tests for a new route, module, or use case.
---

# pytest-async-test

Generate async pytest tests for FastAPI endpoints.

## Instructions

1. Create `tests/test_{module}.py` with:
   - `from typing import Any`
   - Import `AsyncClient` from httpx
   - Import `AsyncSession, async_sessionmaker` from sqlalchemy
   - Import repositories/use cases from `app.modules.{module}`

2. Helper functions pattern:
   ```python
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
       resp = await client.post(
           "/auth/register", json=_register_payload(email=email)
       )
       assert resp.status_code == 201
       return Payload(resp.json())


   async def _login(
       client: AsyncClient, email: str = EMAIL, password: str = PASSWORD
   ) -> Payload:
       resp = await client.post(
           "/auth/token",
           data={"username": email, "password": password},
       )
       assert resp.status_code == 200
       return Payload(resp.json())
   ```

3. Test pattern:
   ```python
   async def test_{action}(client: AsyncClient) -> None:
       # Arrange
       await _register(client)
       tokens = await _login(client)
       headers = {"Authorization": f"Bearer {tokens['access_token']}"}

       # Act
       resp = await client.get("/{module}", headers=headers)

       # Assert
       assert resp.status_code == 200
       assert len(resp.json()["items"]) > 0
   ```

4. Auth test pattern:
   ```python
   async def test_{action}_requires_auth(client: AsyncClient) -> None:
       resp = await client.get("/{module}")
       assert resp.status_code == 401


   async def test_{action}_requires_superuser(
       client: AsyncClient,
       session_factory: async_sessionmaker[AsyncSession],
   ) -> None:
       await _register(client)
       tokens = await _login(client)
       resp = await client.get(
           "/{module}",
           headers={"Authorization": f"Bearer {tokens['access_token']}"}
       )
       assert resp.status_code == 403  # Not superuser
   ```

5. Use `conftest.py` fixtures:
   - `client` - AsyncClient with ASGITransport
   - `session_factory` - async_sessionmaker for direct DB access
   - `_reset_db` - autouse, fresh schema per test

## Conventions

- Test functions: `async def test_{verb}_{noun}(client: AsyncClient) -> None:`
- Use helpers for repeated actions (`_register`, `_login`)
- Assert status codes and response body structure
- Test both success and error paths
- Test auth requirements (401, 403)
- No external services needed (SQLite in-memory, memory rate limiter)
