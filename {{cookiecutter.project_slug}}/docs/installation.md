# Installation

## Requirements

- Python {{ cookiecutter.python_version }}+
- PostgreSQL 16+
- Redis 7+ (optional — caching, Celery and multi-worker rate limiting degrade
  gracefully without it)

## With uv

```bash
git clone https://github.com/youruser/{{ cookiecutter.project_slug }}.git
cd {{ cookiecutter.project_slug }}
uv sync
make init          # creates .env from .env.example
make up            # starts postgres + redis
make migrate
make dev
```

Edit `SECRET_KEY` in `.env` before running anything that matters — the app
refuses to start in production with the placeholder value.

## Without Docker

Point `DATABASE_URL` at SQLite and skip `make up`:

```bash
echo "DATABASE_URL=sqlite+aiosqlite:///./dev.db" >> .env
make migrate
make dev
```

## Everything in Docker

```bash
make docker-up     # builds the image, runs api + db + redis
```

The API is then at `http://localhost:8000` — `/docs` for the schema browser,
`/admin` for the admin panel.
