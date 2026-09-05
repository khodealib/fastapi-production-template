.PHONY: help install init dev up makemigrations migrate worker scheduler format lint test test-fast security verify messages docker-up docker-down docker-logs docker-restart coverage clean schema dev-tools watch docs new-module seed

help: # Show this help
	@grep -E '^[a-zA-Z_-]+:.*?# ' Makefile | awk 'BEGIN {FS = ":.*?# "}; {printf "  %-14s %s\n", $$1, $$2}'

install: # Install deps (uv)
	uv sync

init: # Copy .env.example to .env (first-time setup)
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example — edit SECRET_KEY before running")
	@test -f .env && echo ".env already exists, skipping"

dev: init ## Run dev server with hot-reload (needs db + redis running)
	uv run uvicorn app.main:app --reload

up: # Start postgres + redis
	docker compose up -d db redis

migrate: # Apply DB migrations
	uv run alembic upgrade head

makemigrations: # Autogenerate a migration: make makemigrations m="msg"
	uv run alembic revision --autogenerate -m "$(m)"

worker: # Start a TaskIQ worker
	uv run taskiq worker app.infrastructure.broker:broker

scheduler: # Start the TaskIQ scheduler (enqueues each module's crons/ tasks)
	uv run taskiq scheduler app.infrastructure.scheduler:scheduler

format: # Auto-format + fix
	uv run ruff check --fix app tests && uv run ruff format app tests

lint: # Ruff + mypy
	uv run ruff check app tests
	uv run ruff format --check app tests
	uv run mypy --strict app tests

test: # Run the test suite
	uv run pytest

test-fast: # Run tests in parallel (pytest-xdist, faster on multi-core)
	uv run pytest -n auto --tb=short

security: # Static security scan (bandit)
	uv run bandit -c pyproject.toml -q -r app

coverage: # Run tests with HTML coverage report (opens htmlcov/index.html)
	uv run pytest --cov=app --cov-report=html --cov-report=term-missing

clean: # Remove caches and build artefacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage dist

schema: # Export openapi.json without starting the server
	uv run python scripts/export_schema.py

dev-tools: # Start pgAdmin (localhost:5050) + Mailpit (localhost:8025)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d pgadmin mailpit

watch: # Re-run tests on file change (TDD loop)
	uv run ptw -- --tb=short

docs: # Serve documentation locally (http://localhost:8000)
	uv run mkdocs serve

new-module: # Scaffold a new module: make new-module name=payments
	uv run python -m app.cli new-module $(name)

seed: # Load fixture data into the database (make sure DB is running first)
	uv run python -m app.cli seed

verify: lint security test # Everything a CI job would run

messages: # Compile gettext catalogs (needs babel)
	uv run pybabel compile -d app/locales

docker-up: init ## Start full stack in Docker (builds image + runs api + db + redis)
	docker compose up -d --build

docker-down: # Stop Docker stack
	docker compose down

docker-logs: # Tail Docker logs
	docker compose logs -f

docker-restart: # Rebuild and restart Docker stack
	docker compose up -d --build --force-recreate
