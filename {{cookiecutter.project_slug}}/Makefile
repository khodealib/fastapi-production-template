.PHONY: help install dev migrate makemigrations lint format test verify messages worker

help: # Show this help
	@grep -E '^[a-zA-Z_-]+:.*?# ' Makefile | awk 'BEGIN {FS = ":.*?# "}; {printf "  %-14s %s\n", $$1, $$2}'

install: # Install deps (uv)
	uv sync

dev: # Run dev server with reload
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
