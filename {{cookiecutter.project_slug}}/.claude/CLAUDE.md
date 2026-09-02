# {{ cookiecutter.project_name }}

FastAPI service on Python {{ cookiecutter.python_version }}, managed with `uv`.
Strict `ruff` + `mypy --strict` + `pytest` — `make verify` must stay green.

## Commands

```bash
make install      # uv sync
make init         # create .env from .env.example
make up           # start postgres + redis (docker compose)
make dev          # dev server with reload → /docs, /admin
make migrate      # alembic upgrade head
make makemigrations m="msg"   # autogenerate a migration
make worker       # Celery worker
make test         # pytest
make security     # bandit static security scan
make verify       # ruff + mypy + bandit + pytest (what CI runs)
make lint         # ruff check + format check + mypy
make format       # ruff check --fix + ruff format
```

## Orchestration

You are the orchestrator. Classify the task, **write the plan yourself**, then
delegate the code. The agents in `.claude/agents/` each pin their own model and
carry their own brief, so none of them needs this file loaded.

| Task | Pipeline |
|---|---|
| Simple — typo, docstring, local rename, "where is X" | `quick` |
| Normal coding — a contained feature or fix in one module | `coder` |
| Complex coding | plan here → `implementer` → `reviewer` |
| Architecture, database, security, performance, breaking change | plan here → `implementer` → `reviewer` |
| Critical or high-risk | plan here → `implementer` → `reviewer` → `implementer` (fixes) → `reviewer` (final verification) |

- When a task sits between two rows, take the higher one.
- **A change to a response shape, a status code, an error code, a query
  parameter, or a settings name is a breaking change**, however small the diff —
  a client is parsing it.
- Critical means expensive to undo or hard to notice: auth, the rate limiter,
  migrations, the exception handlers, anything touching another user's data.
- `reviewer` is read-only by design. Route its findings to `implementer` rather
  than asking it to edit.
- If the review returns findings, the fix round is part of the pipeline, not
  optional follow-up.
- Do not write the code yourself on a row that names an agent. `coder` exists so
  that normal coding is delegated too.
- The session's own model is chosen by the user and cannot be switched mid-task.
  This table routes work to agents that pin theirs.

### Planning

For every row above the `coder` line, produce the plan before delegating. It
must state:

1. Which files change, and in what order. A module is `routes.py`, `service.py`,
   `crud.py`, `models.py`, `schemas.py`, `deps.py`, `admin.py` — say which are
   involved.
2. Every place that must move together: a new setting also touches
   `.env.example` and `docs/configuration.md`; a new model also needs a
   migration and an `alembic/env.py` import; a new error also belongs in the
   route's documented responses; anything a client observes also changes
   `docs/api-contract.md`.
3. Whether the change breaks an API contract, and if so what a client parsing
   the old response will see.
4. The tests that prove it, named individually — not "add tests".
5. Anything you are unsure about, named plainly rather than guessed.

Prefer the smallest plan that fully covers the request. Say what must be true
when the work is done, not the code that would do it.

## Skills

`.claude/skills/` holds the templates for the file kinds this service is made
of: `fastapi-route`, `sqlalchemy-model`, `pydantic-schema`, `pytest-async-test`,
`markdown-docs`. They load on demand — reach for the matching one instead of
copying an existing file, and update it when the convention it encodes changes.

## Architecture

Feature-based modules under `{{ cookiecutter.package_name }}/modules/`. Each module follows:
- `routes.py` → HTTP layer (thin; no DB or business logic)
- `service.py` → use cases (classes with `execute()`)
- `crud.py` → repository adapters (data access only)
- `models.py` → SQLAlchemy ORM entities
- `schemas.py` → Pydantic API boundaries
- `deps.py` → FastAPI dependencies, including repository providers
- `admin.py` → SQLAdmin `ModelView`s + `register_admin()`

Keep every use case in `service.py` while the module is small. Split it into a
`usecases/` package — one file per use case, re-exported from its `__init__.py`
— once `service.py` passes roughly 300 lines or 8 use cases, whichever comes
first. Routers get the same treatment at the same threshold. Do not start a
module in the split layout: a package of six-line files is harder to read than
one file.

`core/` holds cross-cutting: config, database, security, exceptions, pagination,
health, **response helpers**, and `openapi.py` (error documentation).
`infrastructure/` holds external integrations: cache, email, i18n, rate limiting, tasks.
`main.py` is the app factory (`create_app()`); `api.py` mounts every module router.

Dependency direction is one-way: `routes → service → crud → models`. Routes never
touch a repository's session directly, services never import FastAPI.

## Conventions

- Session type: `Session = Annotated[AsyncSession, Depends(get_session)]`
- Use cases are classes with an `execute()` method
- Repositories wrap `AsyncSession`, no business logic. `get_session` commits on
  success and rolls back on exception — repositories `flush()`, they don't commit
- Rate limiting is layered. `api_router` carries a global budget
  (`RATE_LIMIT_GLOBAL`, one bucket per client across all endpoints via
  `per_path=False`), so **every** `/api` route can return 429 and documents it.
  A route needing something stricter declares its own dependency:
  ```python
  strict = rate_limit(
      "3/minute",
      strategy=RateLimitStrategy.MOVING_WINDOW,   # per-route algorithm
      key_prefix="password_reset",
  )

  @router.post("/reset", dependencies=[Depends(strict)])
  ```
  Router dependencies run before the route's own, so the narrower limit is the
  one reported in the `X-RateLimit-*` headers. Valid strategies:
  `fixed-window`, `moving-window`, `sliding-window`. Health probes sit outside
  `API_PREFIX` and stay unthrottled
- Callers are identified by `core.net.client_ip`, used by both the limiter and
  the request log. It reads `X-Forwarded-For` only when `TRUSTED_PROXY_HOPS` is
  greater than zero, and takes the entry that many hops from the right — the
  ones your own proxies appended. **`TRUSTED_PROXY_HOPS` must equal the real
  number of proxies**: leave it at 0 when the app is directly exposed, or any
  client can rotate the header and get a fresh budget per request; set it too
  high and the value is attacker-supplied again. Behind one nginx it is 1
- Errors inherit from `AppError` with `status_code` and `code`; raise them, don't
  return them — `register_exception_handlers` renders the envelope
- **All API responses use the envelope pattern** — see `core.response` helpers:
  - `success_response(data, message, request)` — single resource
  - `paginated_response(items, total, params, message, request)` — lists
  - `error_response(exc, request)` — errors (auto-handled by exception handlers)
  - `validation_error_response(errors, message, request)` — 422 validation
- `meta` carries only facts about the request (`request_id`). Pagination is a
  **top-level** member of `EnvelopeList[T]` — it describes the payload, and
  only list responses have one
- Response models: `Envelope[T]`, `EnvelopeList[T]` from `core.schemas`; declare
  an alias per schema (`UserReadEnvelope = Envelope[UserRead]`) and use it as
  `response_model`
- Request ID: `request.state.request_id` for tracing (set by `RequestContextMiddleware`,
  echoed as the `X-Request-ID` header)
- **Document the errors a route can raise** with `core.openapi.error_responses`,
  which reads status code, error code and description off the exception class:
  ```python
  @users_router.get(
      "/{user_id}",
      response_model=UserReadEnvelope,
      responses=error_responses(ForbiddenError, NotFoundError, validation=True),
  )
  ```
  Pass `validation=True` on any route with a body, path or query parameter —
  FastAPI's built-in 422 schema describes a bare list, not this app's envelope.
  Errors shared by every route in a router go on the router itself. Never write
  a helper for the *success* response: `response_model` is its only source of
  truth, and a second declaration is exactly how docs drift from behaviour.
- Repositories are provided by dependencies, not constructed in handlers: use
  `UserRepo` / `RefreshTokenRepo` from the module's `deps.py`
- Pagination: `Depends(page_params)` → `PageParams(page, page_size)`. The
  query parameter, the dataclass field and the response member all use the
  same name, so nothing has to be translated between layers
- Config is read once via `get_settings()` (`lru_cache`d) — never read `os.environ`
  directly; add new knobs to `core/config.py` **and** `.env.example`

**Health probes are the one exception to the envelope.** `/live`, `/ready`, and
`/health` are registered outside `API_PREFIX` and return bare k8s-shaped bodies.
They return a plain `JSONResponse(503)` instead of raising, so the envelope
exception handlers can't re-wrap them. Tests assert that `success`/`data`/`meta`
are absent — don't "fix" them into envelopes.

## Testing

- `pytest-asyncio` in `asyncio_mode = "auto"` — write `async def test_...`, no marker
- `tests/conftest.py` sets env vars (SQLite in-memory, no Redis/SMTP) **before**
  importing the app; keep new imports below that block
- Fixtures: `client` (httpx `AsyncClient` over ASGI), `session_factory`.
  Schema is dropped and recreated per test, and rate-limit caches are cleared
- Use the `mocker` fixture (`pytest-mock`), not `unittest.mock` imports
- To exercise a failing dependency through the full HTTP path, override it via
  `app.dependency_overrides` rather than mocking the check function
- `filterwarnings = ["error"]` — a new warning fails the suite

## Security scanning

`make security` runs bandit over the package (tests are excluded — `assert`
is their point). It must run through `uv run`, never `uvx`: bandit parses
with whatever interpreter it runs on, and a file it cannot parse is **skipped
silently while bandit still exits 0**. On an older interpreter that quietly
means auth code goes unscanned and CI still passes.

Suppress a false positive with a bare `# nosec BXXX` on the offending line
and the justification as a normal comment above it — anything written after
`nosec` is parsed as further test IDs, not as prose. Never skip a whole test
globally; that hides the real cases too. Prefer removing the trigger: a magic
string flagged as a password is usually better as a named constant.

## Adding a Module

1. `modules/<name>/` with the file set above
2. Include its router in `api.py`
3. Import its `models` in `alembic/env.py` so autogenerate sees the tables
4. `make makemigrations m="add <name>"` then `make migrate`
5. Register admin views in `main.py` if the module needs them
6. Add `tests/test_<name>.py`
7. Run `make verify`
