# syntax=docker/dockerfile:1
# Multi-stage: uv sync in builder, slim runtime image.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code and install
COPY {{ cookiecutter.package_name }} ./{{ cookiecutter.package_name }}
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"

# Install only curl for healthcheck (minimal footprint)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only what's needed from builder
COPY --from=builder --chown=app:app /app/.venv .venv
COPY --from=builder /app/{{ cookiecutter.package_name }} ./{{ cookiecutter.package_name }}
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/{{ cookiecutter.package_name }}/alembic ./alembic

# Create non-root user
RUN useradd --create-home --user-group app \
    && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD curl -f http://localhost:8000/live || exit 1

CMD ["uvicorn", "{{ cookiecutter.package_name }}.main:app", "--host", "0.0.0.0", "--port", "8000"]
