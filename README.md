# FastAPI Production Template

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logo=uv&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

**The starting line for production FastAPI services.**  
Batteries included: admin, auth, migrations, tasks, observability — all typed, linted, tested.

---

A cookiecutter template that generates a production-ready FastAPI project with
Django-grade batteries: admin panel, async ORM + migrations, JWT auth, Celery,
structured logging, i18n, email, caching, and multi-strategy rate limiting —
built with feature-based module layout and strict ruff/mypy/pytest under `uv`.

## Use

```bash
# From GitHub
uv run --from cookiecutter cookiecutter https://github.com/khodealib/fastapi-production-template

# From local clone
git clone https://github.com/khodealib/fastapi-production-template.git
cd fastapi-production-template
uv run --from cookiecutter cookiecutter .
```

## Generated Project Layout

```
{project_slug}/
├── pyproject.toml              # uv + ruff/mypy/pytest config
├── Makefile                    # dev commands
├── Dockerfile docker-compose.yml .env.example alembic.ini
├── .claude/                    # Claude AI instructions, agents + skills
│   ├── CLAUDE.md
│   ├── agents/
│   └── skills/
├── app/                        # always `app`, whatever the project is called
│   ├── api.py                  # central router
│   ├── main.py                 # ASGI entrypoint
│   ├── application.py          # app factory
│   ├── config/                 # settings, constants
│   ├── database/               # base, engine, session
│   ├── security/               # jwt, passwords, constants
│   ├── exceptions/             # errors, handlers
│   ├── http/                   # schemas, response, pagination, openapi, net
│   ├── middleware/             # request context, rate-limit headers
│   ├── observability/          # logging, metrics, tracing
│   ├── health/                 # /live, /ready, /health
│   ├── utils/                  # datetime (utcnow) and other shared helpers
│   ├── infrastructure/         # admin_auth, cache, email, i18n, ratelimit, tasks
│   ├── modules/
│   │   └── users/              # routes/, usecases/, repositories/, models/,
│   │                           #   schemas/, deps.py, metrics.py, admin.py
│   ├── alembic/
│   ├── locales/
│   └── static/
├── tests/
└── fixtures/
```

## Features

| Feature | Implementation |
|---|---|
| Admin panel | SQLAdmin at `/admin` (superuser-gated) |
| ORM + migrations | SQLAlchemy 2.0 async + Alembic |
| Auth | JWT access + refresh rotation, argon2 |
| Rate limiting | `limits` library (fixed/moving/sliding window) |
| Email | stdlib SMTP + Jinja2 templates, Celery task |
| Cache | Redis helpers (no-op without `REDIS_URL`) |
| i18n | gettext + Babel |
| Logging | structlog (JSON prod, console dev) |
| Metrics / tracing | Prometheus at `/metrics` (`ENABLE_METRICS`) + OpenTelemetry (`ENABLE_TRACING`, opt-in) |
| Task queue | Celery + Redis |

## Template Development

After editing files under `{{ cookiecutter.project_slug }}/`, verify:

```bash
# Generate fixture project
rm -rf /tmp/final
uvx cookiecutter --no-input --output-dir /tmp/final . \
  project_name="Fixture" project_slug="fixture" \
  description="Test" author_name="T" author_email="t@t.com" version="0.1.0"

# Run verification
cd /tmp/final/fixture
uv sync
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy --strict app tests
uv run pytest -v
```

All four must pass with zero errors.

## Claude AI Configuration

The generated project includes `.claude/skills/`, loaded on demand, with
templates for:

- **fastapi-route** — module route generation
- **sqlalchemy-model** — ORM model patterns
- **pydantic-schema** — request/response schemas
- **pytest-async-test** — async test stubs
- **markdown-docs** — keeping `docs/` true

…and `.claude/agents/` with a model-routing pipeline, each agent pinned to the
model its role warrants and briefed well enough not to load `CLAUDE.md`:

| Agent | Model | Role |
|---|---|---|
| `quick` | Haiku | trivial single-file edits |
| `coder` | Sonnet | contained features and fixes |
| `implementer` | Sonnet | writes the approved plan, and the fix round |
| `reviewer` | Opus | reviews the result, read-only |

Planning stays with the main session, which classifies the task and writes the
plan before delegating.

Complex, architectural, security, performance and breaking changes run
plan → implement → review; critical ones add a fix round and a final
verification pass. The routing table is in `CLAUDE.md`.
