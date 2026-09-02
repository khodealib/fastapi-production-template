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
| `make security` | bandit static security scan |
| `make format` | Auto-fix lint issues |
| `make verify` | Full CI check (lint + security + test) |

## Architecture

The Python package is always named `app` — the directory name does not change
with the project name.

```
app/
├── api.py                  # central router — mounts module routers
├── main.py                 # ASGI entrypoint (`app = create_app()`)
├── application.py          # app factory — middleware + admin + error handling
├── config/
│   ├── settings.py         # pydantic-settings (env vars → typed config)
│   └── constants.py        # Environment enum and friends
├── database/
│   ├── base.py             # DeclarativeBase + naming convention
│   ├── engine.py           # async engine + dispose_engine
│   └── session.py          # SessionFactory, get_session, Session
├── security/
│   ├── jwt.py              # JWT encode/decode
│   ├── passwords.py        # argon2 hashing
│   └── constants.py        # token type / scheme discriminators
├── exceptions/
│   ├── errors.py           # AppError hierarchy
│   └── handlers.py         # envelope-rendering exception handlers
├── http/
│   ├── schemas.py          # CustomModel base + envelope types
│   ├── response.py         # envelope response helpers
│   ├── pagination.py       # Page / page_params helpers
│   ├── openapi.py          # error_responses builder
│   └── net.py              # client_ip behind proxies
├── middleware/
│   ├── request_context.py  # request_id + structured request log
│   └── rate_limit_headers.py
├── observability/
│   ├── logging.py          # structlog configuration
│   ├── metrics.py          # Prometheus, exposed at /metrics
│   └── tracing.py          # OpenTelemetry
├── health/                 # /live, /ready, /health probes
├── utils/
│   └── datetime.py         # utcnow() — the one source of "now"
├── infrastructure/
│   ├── admin_auth.py       # SQLAdmin authentication backend
│   ├── cache.py            # Redis helpers (no-op without REDIS_URL)
│   ├── email.py            # SMTP sender + Jinja2 templates
│   ├── i18n.py             # gettext internationalization
│   ├── ratelimit.py        # rate limiting (fixed/moving/sliding window)
│   └── tasks.py            # Celery app + email task
├── modules/
│   └── users/
│       ├── models/         # SQLAlchemy ORM entities, one per file
│       ├── schemas/        # Pydantic API boundaries
│       ├── repositories/   # Repository adapters (data access)
│       ├── usecases/       # Use cases (business logic), one per file
│       ├── routes/         # HTTP layer (thin), one router per file
│       ├── deps.py         # CurrentUser / SuperUser dependencies
│       ├── metrics.py      # Prometheus counters for this module's events
│       └── admin.py        # SQLAdmin views
└── tests/
```

### Layer Rules

- **routes/** — parses request, calls use case, returns response. No DB logic.
- **usecases/** — one class per file, each with a single `execute()`.
- **repositories/** — adapters wrapping `AsyncSession`. Data access only.
- **models/** — SQLAlchemy ORM entities (the model IS the entity).

Names are spelled out in full: `database/` not `db/`, `repositories/` not
`crud/`, `usecases/` not `services/`. The only abbreviations are the
established ones — `http`, `jwt`, `api`.

`modules/<name>/` is the import boundary: relative imports inside it, absolute
`from app.X import Y` for anything outside. A `from ...` means the import
escaped the module and should have been absolute.

Routers mount at the root: `/auth/token`, `/users/me`. There is no `/api`
prefix.

### Adding a New Module

1. Create `modules/{name}/` with `models/`, `schemas/`, `repositories/`,
   `usecases/`, `routes/`, `deps.py`, and `metrics.py`
2. Add a router under `routes/`:
   ```python
   from fastapi import APIRouter, Depends
   from app.database.session import Session
   from app.http.response import success_response, paginated_response

   {name}_router = APIRouter(prefix="/{name}", tags=["{name}"])

   @{name}_router.get("", response_model=ItemListEnvelope)
   async def list_items(
       request: Request,
       session: Session,
       params: Annotated[PageParams, Depends(page_params)],
   ) -> ItemListEnvelope:
       repo = ItemRepository(session)
       items, total = await ListItems(repo).execute(
           page=params.page, page_size=params.page_size
       )
       return paginated_response(items, total, params, request=request)
   ```
3. Register the module's models in `alembic/env.py`, then mount the router in
   `api.py`:
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
| Metrics / tracing | Prometheus at `/metrics` (`ENABLE_METRICS`) + OpenTelemetry (`ENABLE_TRACING`, opt-in) |
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
  "meta": { "request_id": "abc123" }
}
```

### Success — Paginated List
```json
{
  "success": true,
  "data": [{ "id": "..." }, { "id": "..." }],
  "message": "Users retrieved",
  "errors": null,
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  },
  "meta": { "request_id": "abc123" }
}
```

### Error
```json
{
  "success": false,
  "data": null,
  "message": "User not found",
  "errors": [{ "code": "not_found", "message": "User not found", "field": null }],
  "meta": { "request_id": "abc123" }
}
```

### Validation Error (422)
```json
{
  "success": false,
  "data": null,
  "message": "Validation failed",
  "errors": [{ "code": "validation_error", "message": "Invalid email", "field": "email" }],
  "meta": { "request_id": "abc123" }
}
```

**Field reference:**

| Field | Type | Description |
|---|---|---|
| `success` | bool | `true` for 2xx, `false` for 4xx/5xx |
| `data` | object/array/null | Response payload on success |
| `message` | string/null | Human-readable summary |
| `errors` | array/null | Structured error details on failure |
| `pagination` | object | List responses only: page, page_size, total, total_pages, has_next, has_previous |
| `meta` | object | Request metadata (request_id) |

HTTP status codes remain accurate (200, 201, 400, 401, 404, 409, 422, 500).

## Rate Limiting

```python
from app.infrastructure.ratelimit import rate_limit

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

Plain Markdown in [`docs/`](docs/README.md) — no build step.

| Page | For |
|---|---|
| [API Contract](docs/api-contract.md) | **Frontend and API consumers** — response envelope, error codes, pagination, auth, rate limiting |
| [Installation](docs/installation.md) | Getting it running |
| [Quickstart](docs/quickstart.md) | First requests against a live server |
| [Configuration](docs/configuration.md) | Every environment variable |
| [Architecture](docs/architecture.md) | Layout, layer rules, patterns |
| [Adding Modules](docs/adding-modules.md) | Extending the service |

The live API schema is at `/openapi.json`, browsable at `/docs`.