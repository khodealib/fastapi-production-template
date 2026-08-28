# {{ cookiecutter.project_name }}

## Commands

```bash
make dev          # Run dev server with reload
make migrate      # Apply DB migrations
make test         # Run test suite
make verify       # ruff + mypy + pytest
make lint         # ruff check + format check + mypy
make format       # ruff check --fix + ruff format
make docs         # Build Sphinx docs (en + fa_IR)
make docs-live    # Live-reload docs server
```

## Architecture

Feature-based modules under `modules/`. Each module follows:
- `routes.py` → HTTP layer (no DB logic)
- `service.py` → use cases (classes with `execute()`)
- `crud.py` → repository adapters (data access only)
- `models.py` → SQLAlchemy ORM entities
- `schemas.py` → Pydantic API boundaries
- `deps.py` → FastAPI dependencies
- `interactor.py` → multi-usecase orchestration

`core/` holds cross-cutting: config, database, security, exceptions, health, **response helpers**.
`infrastructure/` holds external integrations: cache, email, i18n, rate limiting, tasks.

## Conventions

- Session type: `Session = Annotated[AsyncSession, Depends(get_session)]`
- Use cases are classes with `execute()` method
- Repositories wrap `AsyncSession`, no business logic
- Rate limiting via `rate_limit("5/minute", key_prefix="login")` dependency
- Errors inherit from `AppError` with status_code and code
- **All responses use envelope pattern** — see `core.response` helpers:
  - `success_response(data, message, request)` — single resource
  - `paginated_response(items, total, params, message, request)` — lists
  - `error_response(exc, request)` — errors (auto-handled by exception handlers)
  - `validation_error_response(errors, message, request)` — 422 validation
- Response models: `Envelope[T]`, `EnvelopeList[T]` from `core.schemas`
- Request ID: `request.state.request_id` for tracing