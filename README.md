# FastAPI Production Template (cookiecutter)

A cookiecutter template that generates a production-ready FastAPI project with
Django-grade batteries: admin panel, ORM + migrations, JWT auth, Celery, CLI
management commands, structured logging, i18n, email, caching, and a
multi-strategy rate limiter — built on pragmatic DDD layering and a strict
ruff/mypy/pytest toolchain under `uv`.

## Use

```bash
uv run --from cookiecutter cookiecutter https://github.com/khodealib/fastapi-production-template
```

or locally:

```bash
uv run --from cookiecutter cookiecutter .
```

See the generated project's `README.md` for the full feature map and
quickstart.

## Layout

```
cookiecutter.json
{{ cookiecutter.project_slug }}/
├── pyproject.toml           # uv project + ruff/mypy/pytest config
├── manage.py                # Typer CLI entrypoint
├── alembic.ini  Makefile  Dockerfile  docker-compose.yml  .env.example
├── {{ cookiecutter.package_name }}/   # the generated app package
└── tests/
```

## Development of the template

Every file under `{{ cookiecutter.project_slug }}/` is Jinja-rendered by
cookiecutter (`{{ ... }}` fields substituted). After edits, re-generate a
fixture project and run `make verify` to prove the template still produces a
green project.
