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
    ├── {{cookiecutter.package_name}}/
    ├── tests/  docs/  fixtures/  templates/
    ├── .claude/CLAUDE.md          # instructions shipped INTO generated projects
    └── .claude/skills/            # fastapi-route, sqlalchemy-model, pydantic-schema,
                                   #   pytest-async-test, sphinx-docs
```

Two CLAUDE.md files, different audiences:

- **This file** — for working *on the template*.
- **`{{cookiecutter.project_slug}}/.claude/CLAUDE.md`** — for agents working in a
  *generated* project. Keep it in sync when module layout or conventions change.

## Templating Rules

Placeholders in use: `{{ cookiecutter.project_name }}`, `project_slug`,
`package_name`, `description`, `author_name`, `author_email`, `version`,
`python_version`, `fastapi_version`.

- `project_slug` is kebab-case (`my-service`), `package_name` is snake_case
  (`my_service`). Use `package_name` for Python imports and module paths,
  `project_slug` for the directory, DB name, and pyproject `name`.
- Directory names are templated too: `{{cookiecutter.package_name}}/` is a real
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

- Import order in the generated project is **package-name dependent** unless
  pinned — `fixture` sorts before `httpx`, `my_api_svc` between, `zqpkgzq` after.
  `[tool.ruff.lint.isort] known-first-party` in `pyproject.toml` pins the package
  into its own trailing section so one committed order is correct for every name.
  Verify with at least two names that bracket the third-party distributions.

## Verifying a Change

Editing files under `{{cookiecutter.project_slug}}/` cannot be linted or tested
in place. Always generate a fixture project and run the real checks against it:

```bash
rm -rf /tmp/final && uvx cookiecutter --no-input --output-dir /tmp/final . \
  project_name="Fixture" project_slug="fixture" package_name="fixture" \
  description="Test" author_name="T" author_email="t@t.com" version="0.1.0" \
  && cd /tmp/final/fixture && uv sync \
  && uv run ruff check fixture tests \
  && uv run ruff format --check fixture tests \
  && uv run mypy --strict fixture tests \
  && uv run pytest -v
```

All four must pass with zero errors. Tests run against in-memory SQLite with
Redis/SMTP disabled (see `tests/conftest.py` — it sets env vars *before* any app
import, so ordering there matters).

## Generated Project Architecture

Feature-based modules under `{{ cookiecutter.package_name }}/modules/`:

| File | Responsibility |
|---|---|
| `routes.py` | HTTP layer — thin, no DB or business logic |
| `service.py` | Use cases: classes with a single `execute()` |
| `crud.py` | Repository adapters wrapping `AsyncSession`, data access only |
| `models.py` | SQLAlchemy 2.0 ORM entities |
| `schemas.py` | Pydantic API boundaries + `Envelope[T]` aliases |
| `deps.py` | FastAPI dependencies (`CurrentUser`, `SuperUser`) |
| `admin.py` | SQLAdmin `ModelView`s + `register_admin()` |

`core/` — cross-cutting: `config`, `database`, `security`, `schemas`,
`response`, `exceptions`, `exception_handlers`, `pagination`, `constants`,
`logging_conf`, `admin_auth`, and the `health/` package.
`infrastructure/` — external integrations: `cache`, `email`, `i18n`,
`ratelimit`, `tasks`.
`main.py` is the app factory (`create_app()`); `api.py` mounts module routers.

**Two response contracts — do not mix them:**

1. **API routes** always return the envelope (`success`/`data`/`message`/
   `errors`/`meta`) via `core.response` helpers. Exception handlers wrap
   `AppError`, `RequestValidationError`, `StarletteHTTPException`, and bare
   `Exception` into the same shape.
2. **Health probes** (`/live`, `/ready`, `/health`, registered before the API
   prefix) return **bare** bodies for k8s. They return a plain `JSONResponse` on
   503 rather than raising, precisely so the envelope handlers don't re-wrap
   them. Tests assert the absence of envelope keys — keep it that way.

Only three rate-limit strategies are valid: `fixed-window`, `moving-window`,
`sliding-window` (`RateLimitStrategy` in `infrastructure/ratelimit.py`). Keep
`.env.example` and the docs aligned with that enum.

## Keep In Sync

A change to the generated app usually touches more than one file:

- New setting → `core/config.py`, `.env.example`, `docs/configuration.rst`
- New module → `modules/<name>/`, `api.py`, `alembic/env.py` import,
  `docs/api/modules.rst`, a test file
- New make target → `Makefile`, template `README.md`, `.claude/CLAUDE.md`
- Changed layout/conventions → `.claude/CLAUDE.md`, `.claude/skills/*.md`,
  `docs/architecture.rst`, both READMEs
- Docs text change → re-run `make docs-translate` so `fa_IR` `.po` files pick up
  the new strings

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
