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
make worker       # TaskIQ worker
make scheduler    # TaskIQ scheduler (enqueues each module's crons/ tasks)
make test         # pytest
make coverage     # pytest with HTML report → htmlcov/index.html
make watch        # re-run tests on file change (TDD)
make schema       # export openapi.json without starting the server
make dev-tools    # start pgAdmin (port 5050) + Mailpit (port 8025)
make clean        # remove caches and build artefacts
make security     # bandit static security scan
make verify       # ruff + mypy + bandit + pytest (what CI runs)
make lint         # ruff check + format check + mypy
make format       # ruff check --fix + ruff format
make new-module name=X   # scaffold a new feature module
make test-fast           # run tests in parallel (faster on multi-core)
make docs                # serve MkDocs documentation locally
make seed                # load fixtures/users.json into the database
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

1. Which files change, and in what order. A module is `routes/`, `usecases/`,
   `repositories/`, `models/`, `schemas/`, `deps.py`, `admin.py`, `metrics.py` —
   say which are involved.
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

The Python package is always `app/`, whatever the project is called.

Feature-based modules under `app/modules/`. Each module is a package of
packages — one responsibility per file, each package re-exporting from its
`__init__.py`:
- `routes/` → HTTP layer (thin; no DB or business logic), one router per file
- `usecases/` → use cases (classes with `execute()`), one per file
- `repositories/` → repository adapters (data access only), one per entity
- `models/` → SQLAlchemy ORM entities, one per file
- `schemas/` → Pydantic API boundaries, grouped by resource
- `deps.py` → FastAPI dependencies, including repository providers
- `admin.py` → SQLAdmin `ModelView`s + `register_admin()`
- `metrics.py` → Prometheus `Counter`/`Histogram`/`Gauge` for business events in
  this module; use cases call them after state changes
- `tasks/` → TaskIQ task definitions for this module (`async def` + `@broker.task`);
  import `broker` from `app.infrastructure.broker` (absolute import, outside the
  module boundary)
- `crons/` → scheduled task definitions for this module: `@broker.task` with a
  `schedule` label (`schedule=[{"cron": "0 2 * * *"}]`), discovered by
  `app.infrastructure.scheduler`

This is the layout from the first file: a new module starts split, it does not
grow into it.

**Always use full, explicit names** — `database/` not `db/`, `repositories/`
not `crud/`, `usecases/` not `service/`. No abbreviations except the
well-established ones (`http/`, `jwt`, `api`).

Cross-cutting concerns live in named packages at the package root, not in a
catch-all `core/`:
- `config/` → `settings.py` (pydantic-settings), `constants.py`
- `database/` → `base.py` (DeclarativeBase), `engine.py`, `session.py`
- `security/` → `jwt.py`, `passwords.py`, `constants.py`
- `exceptions/` → `errors.py` (the `AppError` hierarchy), `handlers.py`
- `http/` → the response contract: `schemas.py`, `response.py`, `pagination.py`,
  `openapi.py`, `net.py`
- `middleware/` → `request_context.py`, `rate_limit_headers.py`
- `observability/` → `logging.py`, `metrics.py` (Prometheus at `/metrics`,
  gated by `ENABLE_METRICS`), `tracing.py` (OpenTelemetry, gated by
  `ENABLE_TRACING`; `setup_tracing` returns the provider and the lifespan in
  `application.py` shuts it down)
- `health/` → the `/live`, `/ready`, `/health` probes
- `utils/` → small cross-cutting helpers with no home of their own —
  `datetime.py` (`utcnow()`, `UTC`). Not a dumping ground: anything with a real
  subject gets its own package

`infrastructure/` holds external integrations: cache, email, i18n, rate limiting,
the TaskIQ `broker.py` and `scheduler.py`, and the SQLAdmin auth backend.
`application.py` is the app factory
(`create_app()`); `main.py` is the two-line ASGI entrypoint; `api.py` mounts
every module router.

Routers mount at the root — `/auth/token`, `/users/me`. There is no `/api`
prefix and no `API_PREFIX` setting.

Dependency direction is one-way: `routes → usecases → repositories → models`.
Routes never touch a repository's session directly, use cases never import
FastAPI.

## Conventions

- **Import style**: within a module (`modules/<name>/`), use relative imports.
  For anything outside the module boundary — cross-cutting packages
  (`app.config`, `app.database`, `app.security`, etc.) — use absolute imports
  (`from app.X import Y`). Never use `...` to escape a module; that is a signal
  to switch to absolute. The same rule applies to the cross-cutting packages
  themselves: `.sibling` inside `http/`, `app.exceptions.errors` to reach out
- Each module's use cases instrument business events via the module's
  `metrics.py`. Import the metric relatively (`from ..metrics import
  user_registrations_total`) and call it after the side effect succeeds or in
  every error path. Do not instrument HTTP-level events in use cases —
  `observability/metrics.py` handles those
- Session type: `Session` from `database.session` — already
  `Annotated[AsyncSession, Depends(get_session)]`
- Use cases are classes with an `execute()` method
- Repositories wrap `AsyncSession`, no business logic. `get_session` commits on
  success and rolls back on exception — repositories `flush()`, they don't commit
- Rate limiting is layered. `api_router` carries a global budget
  (`RATE_LIMIT_GLOBAL`, one bucket per client across all endpoints via
  `per_path=False`), so **every** API route can return 429 and documents it.
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
  `api_router` and stay unthrottled
- Callers are identified by `http.net.client_ip`, used by both the limiter and
  the request log. It reads `X-Forwarded-For` only when `TRUSTED_PROXY_HOPS` is
  greater than zero, and takes the entry that many hops from the right — the
  ones your own proxies appended. **`TRUSTED_PROXY_HOPS` must equal the real
  number of proxies**: leave it at 0 when the app is directly exposed, or any
  client can rotate the header and get a fresh budget per request; set it too
  high and the value is attacker-supplied again. Behind one nginx it is 1
- Errors inherit from `AppError` with `status_code` and `code`; raise them, don't
  return them — `register_exception_handlers` renders the envelope
- **All API responses use the envelope pattern** — see `http.response` helpers:
  - `success_response(data, message, request)` — single resource
  - `paginated_response(items, total, params, message, request)` — lists
  - `error_response(exc, request)` — errors (auto-handled by exception handlers)
  - `validation_error_response(errors, message, request)` — 422 validation
- `meta` carries only facts about the request (`request_id`). Pagination is a
  **top-level** member of `EnvelopeList[T]` — it describes the payload, and
  only list responses have one
- Response models: `Envelope[T]`, `EnvelopeList[T]` from `http.schemas`; declare
  an alias per schema (`UserReadEnvelope = Envelope[UserRead]`) and use it as
  `response_model`
- Request ID: `request.state.request_id` for tracing (set by `RequestContextMiddleware`,
  echoed as the `X-Request-ID` header)
- **Document the errors a route can raise** with `http.openapi.error_responses`,
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
  directly; add new knobs to `config/settings.py` **and** `.env.example`

**Health probes are the one exception to the envelope.** `/live`, `/ready`, and
`/health` are registered before the module routers and return bare k8s-shaped
bodies.
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

1. `modules/<name>/` with the package set above — `models/`, `schemas/`,
   `repositories/`, `usecases/`, `routes/`, `deps.py`, each with an
   `__init__.py` that re-exports its public names
2. Add `<name>/metrics.py` with the module's business counters
3. Add `<name>/tasks/__init__.py` for TaskIQ task definitions (import
   `broker` from `app.infrastructure.broker`)
4. Add `<name>/crons/__init__.py` for scheduled tasks (`@broker.task` with a
   `schedule` label)
5. Include its router in `api.py`
6. Import its models in `alembic/env.py` so autogenerate sees the tables
7. `make makemigrations m="add <name>"` then `make migrate`
8. Register admin views in `application.py` if the module needs them
9. Add `tests/test_<name>.py`
10. Run `make verify`
