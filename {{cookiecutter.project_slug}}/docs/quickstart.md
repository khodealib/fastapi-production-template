# Quickstart

With the server running, these are the first calls worth making. For the full
contract behind these shapes, see [API Contract](api-contract.md).

## 1. Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "StrongPass1!", "full_name": "Test User"}'
```

```json
{
  "success": true,
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "user@example.com",
    "full_name": "Test User",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2026-01-15T10:30:00Z"
  },
  "message": "User registered successfully",
  "errors": null,
  "meta": { "request_id": "…" }
}
```

Passwords must contain an uppercase letter, a lowercase letter, a digit and a
symbol, and be at least 8 characters. A weaker one comes back as `422` with the
rule in `errors[0].message`.

## 2. Log in

Form-encoded, not JSON — the endpoint follows the OAuth2 password form, so the
email goes in a field named `username`.

```bash
curl -X POST http://localhost:8000/auth/token \
  -d "username=user@example.com&password=StrongPass1!"
```

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ…",
    "refresh_token": "eyJ…",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "Login successful",
  "errors": null,
  "meta": { "request_id": "…" }
}
```

## 3. Call a protected endpoint

```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer <access_token>"
```

```json
{
  "success": true,
  "data": { "id": "3fa85f64-…", "email": "user@example.com", "full_name": "Test User",
            "is_active": true, "is_superuser": false, "created_at": "2026-01-15T10:30:00Z" },
  "message": "Current user retrieved",
  "errors": null,
  "meta": { "request_id": "…" }
}
```

## 4. List users (superuser only)

```bash
curl "http://localhost:8000/users?page=1&page_size=20" \
  -H "Authorization: Bearer <admin_access_token>"
```

```json
{
  "success": true,
  "data": [ { "id": "…", "email": "admin@example.com" },
            { "id": "…", "email": "user@example.com" } ],
  "message": "Users retrieved",
  "errors": null,
  "pagination": {
    "page": 1, "page_size": 20, "total": 2,
    "total_pages": 1, "has_next": false, "has_previous": false
  },
  "meta": { "request_id": "…" }
}
```

As a non-superuser the same call returns `403` with a `forbidden` error code.

## 5. Check health

The probes sit outside the API and are deliberately **not** enveloped — they are
read by Kubernetes, not by clients.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "checks": {
    "database": { "status": "ok", "detail": null },
    "redis": { "status": "ok", "detail": "not configured" }
  },
  "version": "{{ cookiecutter.version }}"
}
```

`/live` answers `{"status": "alive"}` without touching a dependency, and
`/ready` reports the same checks as `/health`. All three return `503` with the
same shape when a dependency is unavailable.
