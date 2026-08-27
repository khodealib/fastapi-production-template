#!/bin/sh
set -e

# Run migrations if any exist
if ls /app/{{ cookiecutter.package_name }}/alembic/versions/*.py >/dev/null 2>&1; then
    echo "Running migrations..."
    alembic upgrade head
else
    echo "No migration files found — skipping. Create one with: alembic revision --autogenerate -m 'initial'"
fi

echo "Starting application..."
exec "$@"
