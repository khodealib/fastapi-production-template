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
├── .claude/                    # Claude AI instructions + skills
│   ├── CLAUDE.md
│   └── skills/
├── {package_name}/
│   ├── api.py                  # central router
│   ├── main.py                 # app factory
│   ├── middleware.py
│   ├── core/                   # config, db, security, health, exceptions
│   ├── infrastructure/         # cache, email, i18n, ratelimit, tasks
│   ├── modules/
│   │   └── users/              # routes, service, crud, models, schemas, deps, admin
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
| Task queue | Celery + Redis |

## Template Development

After editing files under `{{ cookiecutter.project_slug }}/`, verify:

```bash
# Generate fixture project
rm -rf /tmp/opencode/final
uvx cookiecutter --no-input --output-dir /tmp/opencode/final . \
  project_name="Fixture" project_slug="fixture" package_name="fixture" \
  description="Test" author_name="T" author_email="t@t.com" version="0.1.0"

# Run verification
cd /tmp/opencode/final/fixture
uv run ruff check fixture tests
uv run ruff format --check fixture tests
uv run mypy --strict fixture
uv run pytest -v
```

All four must pass with zero errors.

## Claude AI Skills

The generated project includes `.claude/skills/` with templates for:

- **fastapi-route** — module route generation
- **sqlalchemy-model** — ORM model patterns
- **pytest-async-test** — async test stubs
- **pydantic-schema** — request/response schemas