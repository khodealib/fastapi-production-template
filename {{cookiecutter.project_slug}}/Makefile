.PHONY: help install init dev up makemigrations migrate worker format lint test verify messages docker-up docker-down docker-logs docker-restart

help: # Show this help
	@grep -E '^[a-zA-Z_-]+:.*?# ' Makefile | awk 'BEGIN {FS = ":.*?# "}; {printf "  %-14s %s\n", $$1, $$2}'

install: # Install deps (uv)
	uv sync

init: # Copy .env.example to .env (first-time setup)
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example — edit SECRET_KEY before running")
	@test -f .env && echo ".env already exists, skipping"

dev: init ## Run dev server with hot-reload (needs db + redis running)
	uv run uvicorn {{ cookiecutter.package_name }}.main:app --reload

up: # Start postgres + redis
	docker compose up -d db redis

migrate: # Apply DB migrations
	uv run alembic upgrade head

makemigrations: # Autogenerate a migration: make makemigrations m="msg"
	uv run alembic revision --autogenerate -m "$(m)"

worker: # Start a Celery worker
	uv run celery -A {{ cookiecutter.package_name }}.infrastructure.tasks.celery_app worker --loglevel=info

format: # Auto-format + fix
	uv run ruff check --fix {{ cookiecutter.package_name }} tests && uv run ruff format {{ cookiecutter.package_name }} tests

lint: # Ruff + mypy
	uv run ruff check {{ cookiecutter.package_name }} tests
	uv run ruff format --check {{ cookiecutter.package_name }} tests
	uv run mypy --strict {{ cookiecutter.package_name }} tests

test: # Run the test suite
	uv run pytest

verify: lint test # Everything a CI job would run

messages: # Compile gettext catalogs (needs babel)
	uv run pybabel compile -d {{ cookiecutter.package_name }}/locales

docker-up: init ## Start full stack in Docker (builds image + runs api + db + redis)
	docker compose up -d --build

docker-down: # Stop Docker stack
	docker compose down

docker-logs: # Tail Docker logs
	docker compose logs -f

docker-restart: # Rebuild and restart Docker stack
	docker compose up -d --build --force-recreate
