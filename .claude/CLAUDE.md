# CLAUDE.md

## What This Repo Is

A **cookiecutter template**, not a runnable application. Nothing here imports or
executes as-is — every source file lives under `{{cookiecutter.project_slug}}/`
and is full of Jinja placeholders that only resolve when a project is generated.

```
.
├── cookiecutter.json              # prompts + _copy_without_render list
├── README.md                      # template docs (for template users)
└── {{cookiecutter.project_slug}}/ # ← everything the generated project gets
    ├── app/                       # the package — a fixed name, not templated
    ├── tests/  docs/  fixtures/  templates/
    ├── .claude/CLAUDE.md          # instructions shipped INTO generated projects
    └── .claude/skills/<name>/SKILL.md  # fastapi-route, sqlalchemy-model, pydantic-schema,
                                   #   pytest-async-test, markdown-docs
```

Two CLAUDE.md files, different audiences:

- **This file** — for working *on the template*.
- **`{{cookiecutter.project_slug}}/.claude/CLAUDE.md`** — for agents working in a
  *generated* project. Keep it in sync when module layout or conventions change.

## Templating Rules

Placeholders in use: `{{ cookiecutter.project_name }}`, `project_slug`,
`description`, `author_name`, `author_email`, `version`, `python_version`,
`fastapi_version`.

- `project_slug` is kebab-case (`my-service`) and names the directory, the DB,
  and pyproject `name`. There is **no `package_name`**: the Python package is
  always the literal directory `app/`, so every import in every generated
  project reads `from app...`.
- Directory names are templated too: `{{cookiecutter.project_slug}}/` is a real
  directory name on disk. Quote paths in shell commands.
- `pyproject.toml` uses Jinja control flow (`{% if %}`) for the FastAPI version
  pin — it is a **template, not valid TOML**. Same for any file with `{% %}`.
- **`_copy_without_render` in `cookiecutter.json`** lists globs copied verbatim:
  `*.html`, `.gitignore`, `.pre-commit-config.yaml`, `**/locales/**`,
  `templates/**`. Placeholders inside those files are **never substituted** — they
  ship literally into the generated project. Do not add `cookiecutter.*`
  references there. The list is deliberately minimal: `templates/**` and `*.html`
  are Jinja email templates whose `{{ }}` is evaluated at *runtime*, not at
  generation time.
- The CI files **are** rendered, so every GitHub Actions `${{ ... }}` expression in
  `.github/workflows/` is wrapped in `{% raw %}…{% endraw %}` to survive
  generation. Adding a new expression without that wrapper makes cookiecutter
  either fail or silently eat it.

- `[tool.ruff.lint.isort] known-first-party = ["app"]` in `pyproject.toml` pins
  the package into its own trailing import section. Keep it — `app` sorts before
  most third-party distributions, and only that pin keeps one committed import
  order correct.

## Verifying a Change

Editing files under `{{cookiecutter.project_slug}}/` cannot be linted or tested
in place. Always generate a fixture project and run the real checks against it:

```bash
rm -rf /tmp/final && uvx cookiecutter --no-input --output-dir /tmp/final . \
  project_name="Test Service" project_slug="fixture" \
  description="Test" author_name="T" author_email="t@t.com" version="0.1.0" \
  python_version="3.13" \
  && cd /tmp/final/fixture && uv sync \
  && uv run ruff check app tests \
  && uv run ruff format --check app tests \
  && uv run mypy --strict app tests \
  && uv run pytest -v
```

All four must pass with zero errors. Tests run against in-memory SQLite with
Redis/SMTP disabled (see `tests/conftest.py` — it sets env vars *before* any app
import, so ordering there matters).

## Generated Project Architecture

Feature-based modules under `app/modules/`. Each layer is a **package** from
the first file, re-exporting its public names from `__init__.py`:

| Package / file | Responsibility |
|---|---|
| `routes/` | HTTP layer — thin, no DB or business logic; one router per file |
| `usecases/` | Use cases: one class with a single `execute()` per file |
| `repositories/` | Repository adapters wrapping `AsyncSession`, data access only |
| `models/` | SQLAlchemy 2.0 ORM entities, one per file |
| `schemas/` | Pydantic API boundaries + `Envelope[T]` aliases |
| `deps.py` | FastAPI dependencies (`CurrentUser`, `SuperUser`) |
| `admin.py` | SQLAdmin `ModelView`s + `register_admin()` |
| `metrics.py` | Prometheus `Counter`/`Histogram`/`Gauge` for business events in this module; use cases call them after state changes |
| `tasks/` | TaskIQ task definitions for this module (`async def` + `@broker.task`); import `broker` from `app.infrastructure.broker` |
| `crons/` | Scheduled tasks for this module — `@broker.task` carrying a `schedule` label (`schedule=[{"cron": "0 2 * * *"}]`), discovered by `app.infrastructure.scheduler` |

**Always use full, explicit names** — `database/` not `db/`, `repositories/`
not `crud/`, `usecases/` not `service/`. No abbreviations except the
well-established ones (`http/`, `jwt`, `api`).

Cross-cutting concerns are named packages at the package root — there is no
`core/`:

| Package | Holds |
|---|---|
| `config/` | `settings.py` (pydantic-settings), `constants.py` |
| `database/` | `base.py` (DeclarativeBase), `engine.py`, `session.py` |
| `security/` | `jwt.py`, `passwords.py`, `constants.py` |
| `exceptions/` | `errors.py` (`AppError` hierarchy), `handlers.py` |
| `http/` | `schemas.py`, `response.py`, `pagination.py`, `openapi.py`, `net.py` |
| `middleware/` | `request_context.py`, `rate_limit_headers.py` |
| `observability/` | `logging.py`, `metrics.py` (Prometheus), `tracing.py` (OTel) |
| `health/` | the `/live`, `/ready`, `/health` probes |
| `utils/` | `datetime.py` (`utcnow()`, `UTC`) — cross-cutting helpers with no home of their own |

`infrastructure/` — external integrations: `admin_auth`, `broker` (the TaskIQ
broker instance), `scheduler` (the `TaskiqScheduler`, run as its own process via
`make scheduler`), `cache`, `email`, `i18n`, `ratelimit`.
`application.py` is the app factory (`create_app()`); `main.py` is the two-line
ASGI entrypoint; `api.py` mounts module routers **at the root** — there is no
`/api` prefix and no `API_PREFIX` setting.

**Two response contracts — do not mix them:**

1. **API routes** always return the envelope (`success`/`data`/`message`/
   `errors`/`meta`) via `http.response` helpers. Exception handlers wrap
   `AppError`, `RequestValidationError`, `StarletteHTTPException`, and bare
   `Exception` into the same shape.
2. **Health probes** (`/live`, `/ready`, `/health`, registered before the
   module routers) return **bare** bodies for k8s. They return a plain `JSONResponse` on
   503 rather than raising, precisely so the envelope handlers don't re-wrap
   them. Tests assert the absence of envelope keys — keep it that way.

The `responses=` map on a route is generated by `http.openapi.error_responses`
from the `AppError` subclasses it can raise — so an error class's **docstring is
its OpenAPI description and its default message**. It must be the first
statement in the class body; placed after the attributes it is an expression,
`__doc__` is None, and the default message silently becomes the generic one.
`tests/test_openapi.py` guards this.

Only three rate-limit strategies are valid: `fixed-window`, `moving-window`,
`sliding-window` (`RateLimitStrategy` in `infrastructure/ratelimit.py`). Keep
`.env.example` and the docs aligned with that enum.

**Import style**: within a module (`modules/<name>/`), use relative imports. For
anything outside the module boundary — cross-cutting packages (`app.config`,
`app.database`, `app.security`, etc.) — use absolute imports (`from app.X import
Y`). Never use `...` to escape a module; that is a signal to switch to absolute.
The same rule governs the cross-cutting packages themselves: `.sibling` within
`http/`, `app.exceptions.errors` to reach out of it. `grep -rn "^from \.\.\."
app/modules/` in a generated project must come back empty.

Each module's use cases instrument business events via the module's
`metrics.py` (`from ..metrics import user_registrations_total`), called after the
side effect succeeds or in every error path. HTTP-level instrumentation stays in
`observability/metrics.py`.

## Keep In Sync

A change to the generated app usually touches more than one file:

- New setting → `config/settings.py`, `.env.example`, `docs/configuration.md`
- New module → `modules/<name>/` (the full package set, including `metrics.py`),
  `api.py`, an `alembic/env.py` import per entity, a test file
- New make target → `Makefile`, template `README.md`, the shipped `.claude/CLAUDE.md`
- Changed layout/conventions → `.claude/CLAUDE.md`, `.claude/skills/*/SKILL.md`,
  `docs/architecture.md`, both READMEs
- Anything a client can observe — a field, status code, error code, header, or
  query parameter → `docs/api-contract.md`, in the same commit

## Orchestration

You are the orchestrator. Classify the task, **write the plan yourself**, then
delegate the code. The agents live in `.claude/agents/` and each pins its own
model and carries its own brief, so none of them needs this file loaded.

| Task | Pipeline |
|---|---|
| Simple — typo, docstring, local rename, "where is X" | `quick` (Haiku) |
| Normal coding — a contained feature or fix in one area | `coder` (Sonnet) |
| Complex coding | plan here → `implementer` → `reviewer` |
| Architecture, database, security, performance, breaking change | plan here → `implementer` → `reviewer` |
| Critical or high-risk | plan here → `implementer` → `reviewer` → `implementer` (fixes) → `reviewer` (final verification) |

Rules for the classification itself:

- When a task sits between two rows, take the higher one. Misjudging a breaking
  change as normal coding costs far more than one extra review pass.
- **Anything that changes a response shape, a settings name, an exception code,
  a query parameter, or `cookiecutter.json` is a breaking change**, however
  small the diff. Every generated project inherits it.
- A change is critical when getting it wrong is expensive to undo or hard to
  notice: auth, the rate limiter, migrations, the exception handlers, or
  anything a client parses.
- `reviewer` is read-only by design. Do not ask it to edit; route its findings
  to `implementer`.
- The review is not a formality. If it returns findings, the fix round is part
  of the pipeline, not optional follow-up work.
- Do not write the code yourself on a row that names an agent. `coder` exists so
  that normal coding is delegated too.
- The session's own model is chosen by the user and cannot be switched
  mid-task. This table routes work to agents that pin theirs; it does not
  reassign the top-level session.

### Planning

For every row above the `coder` line, produce the plan before delegating. It
must state:

1. Which files change, and in what order.
2. Every place that must move together — see **Keep In Sync** above; a changed
   response shape also touches the tests, both READMEs, `docs/api-contract.md`,
   and the shipped `.claude/CLAUDE.md`.
3. Whether the change breaks an existing contract, and if so what a client that
   depends on the old behaviour will see.
4. The exact verification: which generated fixture names to test with, and what
   the four checks must show.
5. Anything you are unsure about, named plainly rather than guessed.

Do not describe the code line by line. Say what must be true when the work is
done, and prefer the smallest plan that fully covers the request.

## Commit Convention

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>
```

**Types:**

| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring, no feature/fix |
| `test` | Adding/updating tests |
| `chore` | Build, CI, tooling, dependencies |
| `ci` | CI/CD configuration |
| `perf` | Performance improvement |
| `revert` | Reverting a commit |

**Rules:**

- Description: imperative mood, lowercase, no period, max 72 chars
- No `Update`, `Add`, `Fix` as description starters — use imperative: `update` not `Updated`
- Scope optional: `feat(auth): add JWT refresh`
- Breaking changes: `feat!: drop Python 3.11 support`

**Examples:**

```
chore: initial cookiecutter scaffolding
feat: add users module with full auth flow
fix: Dockerfile for correct build and runtime
ci: add GitHub Actions workflow
docs: update READMEs and fix test imports
refactor: use fastapi[standard] and drop redundant uvicorn[standard]
test: add test suite with health and user flow tests
```
