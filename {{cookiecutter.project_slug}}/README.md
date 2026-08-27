# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

A production-ready FastAPI template with Django-like batteries — organized
with feature-based module layout and tuned dev tooling (uv, ruff, mypy, pytest).

## Feature map (Django → here)

| Django | This template |
|---|---|
| `/admin` | SQLAdmin at `/admin` (superuser-gated) |
| ORM + migrations | SQLAlchemy 2.0 async + Alembic (`make migrate` / `make makemigrations`) |
| User auth / permissions | JWT access + refresh (rotation), argon2, `CurrentUser`/`SuperUser` deps |
| Forms / validation | Pydantic v2 schemas per module |
| Templates | Jinja2 (SQLAdmin + email templates) |
| Static/media | `/media` mount (S3-swappable in settings) |
| Email | `send_email` via stdlib SMTP, runs as a Celery task |
| Task queue | Celery + Redis (`worker`, `beat` in docker-compose) |
| Fixtures / seeding | JSON fixtures in `fixtures/` |
| Logging | structlog (JSON in prod, console in dev) + request-id middleware |
| Cache framework | Redis helpers in `cache.py` (no-op without `REDIS_URL`) |
| i18n | gettext + Babel (`locales/`), locale-aware `tr()` |
| Paginator | `Page` / `page_params` helpers |
| Security stack | CORS, TrustedHost, GZip, rate limiting |

## Quickstart

```bash
# 1. generate a new project from this template
uv run --from cookiecutter cookiecutter .
# answer the prompts, then:
cd <project_slug>

# 2. install
uv sync

# 3. run the stack (Postgres + Redis via docker-compose)
make up
make migrate
make dev                # http://localhost:8000/docs | /admin

# 4. check everything in one shot
make verify             # ruff + mypy + pytest
```

No Docker? Set `DATABASE_URL=sqlite+aiosqlite:///./dev.db` in `.env` and
`make dev` — everything except the rate limiter/Celery still works (those
fall back to memory/eager modes).

## Architecture

```
{{ cookiecutter.package_name }}/
├── api.py               # central router — mounts all module routers
├── main.py              # app factory — root urls + middleware + admin
├── middleware.py         # request context + rate-limit headers
├── logging_conf.py      # structlog configuration
├── pagination.py        # Page / page_params helpers
├── core/
│   ├── config.py        # pydantic-settings (Django SETTINGS)
│   ├── constants.py     # Environment enum
│   ├── database.py      # async engine, session dep, naming convention
│   ├── exceptions.py    # AppError hierarchy
│   ├── health/          # /health, /live probes
│   ├── logging_conf.py  # structlog setup
│   ├── pagination.py    # Page / page_params
│   ├── schemas.py       # CustomModel base
│   └── security.py      # JWT encode/decode, argon2 hashing
├── infrastructure/
│   ├── cache.py         # Redis helpers (no-op without REDIS_URL)
│   ├── email.py         # SMTP + Jinja2 email sender
│   ├── i18n.py          # gettext-based i18n
│   ├── ratelimit.py     # multi-strategy rate limiting (limits)
│   └── tasks.py         # Celery app + send_email_task
├── modules/
│   └── users/
│       ├── models.py    # SQLAlchemy ORM entities
│       ├── schemas.py   # Pydantic API boundaries
│       ├── crud.py      # Repository adapters (data access)
│       ├── service.py   # Use cases (business logic)
│       ├── interactor.py# Multi-usecase orchestration
│       ├── deps.py      # get_current_user / require_superuser
│       ├── routes.py    # Thin HTTP layer
│       └── admin.py     # SQLAdmin views
└── tests/
```

**Layer rules:**
- `routes.py` parses and returns; never touches the DB directly.
- `service.py` holds business use cases.
- `crud.py` only accesses data.
- `interactor.py` orchestrates multiple use cases when a single request needs them.
- The SQLAlchemy ORM model **is** the entity — split out a pure domain entity
  only when business rules demand it.

## Rate limiting

`ratelimit.py` wraps [`limits`](https://pypi.org/project/limits/) and exposes
three strategies — `fixed-window`, `moving-window`, `sliding-window` — over
pluggable storage (memory in dev, Redis in prod for multi-worker correctness):

```python
from {{ cookiecutter.package_name }}.infrastructure.ratelimit import rate_limit

@router.post("/token", dependencies=[Depends(rate_limit("5/minute", key_prefix="login"))])
async def login(...): ...
```

Pick the default strategy via `RATE_LIMIT_STRATEGY`; each route can override.
`X-RateLimit-*` response headers are added by `RateLimitHeadersMiddleware`.

## Tooling

- **uv** — dependency + env management (`[dependency-groups] dev`).
- **ruff** — lint+format; tuned ruleset incl. `flake8-type-checking` so
  import-only types never run at runtime.
- **mypy** — strict mode with the `pydantic` and `sqlalchemy` plugins.
- **pytest** — async client (httpx ASGI), per-test isolated SQLite schema,
  rate-limiter reset, no external services required.

Run `make verify` (ruff + format check + mypy + pytest) before committing.

## Production checklist

- Set `ENVIRONMENT=production`, a real `SECRET_KEY`, `ALLOWED_HOSTS`,
  `CORS_ORIGINS`, `DATABASE_URL`, and `RATE_LIMIT_STORAGE_URI=redis://...`.
- Point Celery at Redis; scale `worker` separately.
- Migrations are static and reversible; name them descriptively
  (`make makemigrations m="add-user-bio"`).
- `LOG_JSON=true` for structured logs into your collector.
