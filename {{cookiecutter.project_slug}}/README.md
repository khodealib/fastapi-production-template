# {{ cookiecutter.project_name }}

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logo=uv&logoColor=white)

**The starting line for production FastAPI services.**  
Batteries included: admin, auth, migrations, tasks, observability — all typed, linted, tested.

---

{{ cookiecutter.description }}

A production-ready FastAPI project with Django-like batteries — async ORM, JWT auth,
admin panel, rate limiting, email, i18n, Celery tasks, and strict dev tooling.

## Quickstart

```bash
# Install
uv sync

# Run (Postgres + Redis via docker-compose)
make up
make migrate
make dev                    # http://localhost:8000/docs | /admin

# Or without Docker — set SQLite in .env
echo "DATABASE_URL=sqlite+aiosqlite:///./dev.db" >> .env
make dev

# Verify everything
make verify                 # ruff + mypy + pytest
```

## Commands

| Command | Description |
|---|---|
| `make dev` | Run dev server with reload |
| `make migrate` | Apply DB migrations |
| `make makemigrations m="msg"` | Autogenerate migration |
| `make test` | Run test suite |
| `make lint` | ruff check + format check + mypy |
| `make format` | Auto-fix lint issues |
| `make verify` | Full CI check (lint + test) |
| `make docs` | Build Sphinx docs (en + fa_IR) |
| `make docs-live` | Live-reload docs server |

## Architecture

```
{{ cookiecutter.package_name }}/
├── api.py                  # central router — mounts module routers
├── main.py                 # app factory — middleware + admin + error handling
├── middleware.py           # request context + rate-limit headers
├── core/
│   ├── config.py           # pydantic-settings (env vars → typed config)
│   ├── database.py         # async engine, session dependency
│   ├── security.py         # JWT encode/decode, argon2 hashing
│   ├── exceptions.py       # AppError hierarchy
│   ├── schemas.py          # CustomModel base + envelope types
│   ├── health/             # /health, /live probes
│   ├── pagination.py       # Page / page_params helpers
│   └── response.py         # envelope response helpers
├── infrastructure/
│   ├── cache.py            # Redis helpers (no-op without REDIS_URL)
│   ├── email.py            # SMTP sender + Jinja2 templates
│   ├── i18n.py             # gettext internationalization
│   ├── ratelimit.py        # rate limiting (fixed/moving/sliding window)
│   └── tasks.py            # Celery app + email task
├── modules/
│   └── users/
│       ├── models.py       # SQLAlchemy ORM entities
│       ├── schemas.py      # Pydantic API boundaries
│       ├── crud.py         # Repository adapters (data access)
│       ├── service.py      # Use cases (business logic)
│       ├── interactor.py   # Multi-usecase orchestration
│       ├── deps.py         # CurrentUser / SuperUser dependencies
│       ├── routes.py       # HTTP layer (thin)
│       └── admin.py        # SQLAdmin views
└── tests/
```

### Layer Rules

- **routes.py** — parses request, calls use case, returns response. No DB logic.
- **service.py** — use cases as classes with `execute()` method.
- **crud.py** — repository adapters wrapping `AsyncSession`. Data access only.
- **interactor.py** — orchestrates multiple services for complex flows.
- **models.py** — SQLAlchemy ORM entities (the model IS the entity).

### Adding a New Module

1. Create `modules/{name}/` with `models.py`, `schemas.py`, `crud.py`, `service.py`, `routes.py`, `deps.py`
2. Add routes in `routes.py`:
   ```python
   from fastapi import APIRouter, Depends
   from ...core.database import get_session
   from ...core.response import success_response, paginated_response

   {name}_router = APIRouter(prefix="/{name}", tags=["{name}"])

   @{name}_router.get("", response_model=ItemListEnvelope)
   async def list_items(
       request: Request,
       session: Session,
       params: Annotated[PageParams, Depends(page_params)],
   ) -> ItemListEnvelope:
       repo = ItemRepository(session)
       items, total = await ListItems(repo).execute(page=params.page, size=params.size)
       return paginated_response(items, total, params, request=request)
   ```
3. Register in `api.py`:
   ```python
   from .modules.{name}.routes import {name}_router
   api_router.include_router({name}_router)
   ```

## Feature Map

| Django | This project |
|---|---|
| `/admin` | SQLAdmin at `/admin` (superuser-gated) |
| ORM + migrations | SQLAlchemy 2.0 async + Alembic |
| Auth | JWT access + refresh (rotation), argon2 |
| Forms | Pydantic v2 schemas per module |
| Email | `send_email` via stdlib SMTP + Celery |
| Task queue | Celery + Redis |
| Cache | Redis helpers (memory fallback) |
| i18n | gettext + Babel |
| Logging | structlog (JSON prod, console dev) |
| Rate limiting | `limits` library (3 strategies) |
| Security | CORS, TrustedHost, GZip |

## API Response Format

All endpoints return a consistent envelope structure:

### Success — Single Resource
```json
{
  "success": true,
  "data": { "id": "...", "email": "..." },
  "message": "User created successfully",
  "errors": null,
  "meta": { "request_id": "abc123", "pagination": null }
}
```

### Success — Paginated List
```json
{
  "success": true,
  "data": [{ "id": "..." }, { "id": "..." }],
  "message": "Users retrieved",
  "errors": null,
  "meta": {
    "request_id": "abc123",
    "pagination": { "page": 1, "size": 20, "total": 100, "pages": 5 }
  }
}
```

### Error
```json
{
  "success": false,
  "data": null,
  "message": "User not found",
  "errors": [{ "code": "not_found", "message": "User not found", "field": null }],
  "meta": { "request_id": "abc123", "pagination": null }
}
```

### Validation Error (422)
```json
{
  "success": false,
  "data": null,
  "message": "Validation failed",
  "errors": [{ "code": "validation_error", "message": "Invalid email", "field": "email" }],
  "meta": { "request_id": "abc123", "pagination": null }
}
```

**Field reference:**

| Field | Type | Description |
|---|---|---|
| `success` | bool | `true` for 2xx, `false` for 4xx/5xx |
| `data` | object/array/null | Response payload on success |
| `message` | string/null | Human-readable summary |
| `errors` | array/null | Structured error details on failure |
| `meta` | object | Request metadata (request_id, pagination) |

HTTP status codes remain accurate (200, 201, 400, 401, 404, 409, 422, 500).

## Rate Limiting

```python
from {{ cookiecutter.package_name }}.infrastructure.ratelimit import rate_limit

@router.post("/login", dependencies=[Depends(rate_limit("5/minute", key_prefix="login"))])
async def login(...): ...
```

Strategies: `fixed-window`, `moving-window`, `sliding-window`.
Set via `RATE_LIMIT_STRATEGY` in `.env`. Headers added by `RateLimitHeadersMiddleware`.

## Configuration

All settings via environment variables (or `.env`):

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `test`, `production` |
| `SECRET_KEY` | dev key | JWT signing key (required in prod) |
| `DATABASE_URL` | postgres | Async database URL |
| `REDIS_URL` | `None` | Cache/task queue (optional) |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | `redis://` in prod |
| `LOG_JSON` | `false` | JSON logging in prod |
| `SMTP_HOST` | `None` | Email server (optional) |

## Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set a real `SECRET_KEY` (32+ bytes)
- [ ] Configure `ALLOWED_HOSTS` and `CORS_ORIGINS`
- [ ] Set `DATABASE_URL` to PostgreSQL
- [ ] Set `RATE_LIMIT_STORAGE_URI=redis://...`
- [ ] Configure `SMTP_HOST` for email
- [ ] Set `LOG_JSON=true` for structured logging
- [ ] Run `make migrate` to apply migrations

## Documentation

Build multi-language docs:
```bash
make docs          # builds en/ and fa_IR/
make docs-live     # live-reload server
```

Docs deploy automatically to GitHub Pages on push to `main`.