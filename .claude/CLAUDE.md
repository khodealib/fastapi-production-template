# Claude Project Instructions

## Project Overview

This is a **cookiecutter template** for production-ready FastAPI projects. It generates a complete project structure with Django-like batteries.

**Template location:** Root directory contains `cookiecutter.json` and `{{cookiecutter.project_slug}}/` template.

**Generated project:** When users run `cookiecutter .`, they get a project inside `{{cookiecutter.project_slug}}/`.

## Key Commands

```bash
# Generate project from template
uvx cookiecutter --no-input . project_name="My App" project_slug="my_app" package_name="my_app"

# Run verification on generated project
cd /tmp/opencode/final/my_app
uv run ruff check my_app tests
uv run ruff format --check my_app tests
uv run mypy --strict my_app
uv run pytest -v
```

## Architecture (Generated Project)

```
{{cookiecutter.package_name}}/
├── api.py              # Central router mounting all module routers
├── main.py             # App factory with middleware stack
├── middleware.py        # Request context + rate-limit headers
├── core/
│   ├── config.py       # pydantic-settings (Django SETTINGS equivalent)
│   ├── constants.py    # Environment enum
│   ├── database.py     # Async SQLAlchemy engine + session
│   ├── exceptions.py   # AppError hierarchy
│   ├── health/         # /health and /live probes
│   ├── logging_conf.py # structlog setup
│   ├── pagination.py   # Page/page_params helpers
│   ├── schemas.py      # CustomModel base
│   └── security.py     # JWT + argon2 hashing
├── infrastructure/
│   ├── cache.py        # Redis helpers (no-op without REDIS_URL)
│   ├── email.py        # SMTP sender
│   ├── i18n.py         # gettext internationalization
│   ├── ratelimit.py    # limits library wrapper
│   └── tasks.py        # Celery app
├── modules/
│   └── users/
│       ├── models.py    # SQLAlchemy ORM
│       ├── schemas.py   # Pydantic boundaries
│       ├── crud.py      # Repository adapters
│       ├── service.py   # Use cases
│       ├── interactor.py# Multi-usecase orchestration
│       ├── deps.py      # FastAPI dependencies
│       ├── routes.py    # HTTP layer
│       └── admin.py     # SQLAdmin views
└── tests/
```

## Conventions

### Code Style
- **Formatter/Linter:** ruff (check + format)
- **Type checker:** mypy --strict
- **Max line length:** 88 characters
- **Import order:** stdlib → third-party → local (ruff isort handles this)

### File Naming
- Module directories: `modules/{feature_name}/`
- Routes: `routes.py` (not `api.py` to avoid confusion with `api_router`)
- Use cases: `service.py` (not `usecases.py`)
- Repositories: `crud.py` (not `repositories.py`)

### Patterns
- **Use cases** are classes with `execute()` method in `service.py`
- **Interactors** orchestrate multiple use cases in `interactor.py`
- **Repositories** are classes wrapping `AsyncSession` in `crud.py`
- **Dependencies** use `Annotated` type aliases in `deps.py`
- **Session type:** `Session = Annotated[AsyncSession, Depends(get_session)]`

### Testing
- **Framework:** pytest + pytest-asyncio
- **Client:** httpx AsyncClient with ASGITransport
- **DB:** SQLite in-memory, fresh schema per test
- **Rate limiting:** memory-backed, reset per test

## Verification

Before committing, always run on the **generated project**:

```bash
uv run ruff check fixture_project tests
uv run ruff format --check fixture_project tests  
uv run mypy --strict fixture_project
uv run pytest -v
```

All must pass with zero errors.

## Cookiecutter Variables

- `project_name`: Display name (e.g., "My Project")
- `project_slug`: Python package-safe name (e.g., "my_project")
- `package_name`: Import name (usually same as `project_slug`)
- `description`: Short project description
- `author_name`: Author name
- `author_email`: Author email
- `version`: Initial version (default: "0.1.0")

## Notes

- The `{{cookiecutter.project_slug}}/README.md` is for the **generated** project
- The root `README.md` is for the **template** itself
- Infrastructure services (Redis, SMTP) gracefully degrade when unavailable
- Rate limiting uses memory in dev, requires Redis URI in production
