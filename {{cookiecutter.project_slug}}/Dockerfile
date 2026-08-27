# syntax=docker/dockerfile:1
# Multi-stage: uv sync in builder, slim runtime image.
FROM ghcr.io/astral-sh/uv:python{{ cookiecutter.python_version }}-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached layer)
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# Copy application code and install
COPY {{ cookiecutter.package_name }} ./{{ cookiecutter.package_name }}
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# ---------------------------------------------------------------------------
# Runtime image
# ---------------------------------------------------------------------------
FROM python:{{ cookiecutter.python_version }}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"

# Install only curl for healthcheck (minimal footprint)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --user-group app

WORKDIR /app

# Copy everything with correct ownership in one layer
COPY --from=builder --chown=app:app /app/.venv .venv
COPY --from=builder --chown=app:app /app/{{ cookiecutter.package_name }} ./{{ cookiecutter.package_name }}
COPY --from=builder --chown=app:app /app/alembic.ini ./alembic.ini
COPY --chown=app:app entrypoint.sh ./

# Create writable directories for the app
RUN mkdir -p /app/media /app/static \
    && chmod +x /app/entrypoint.sh \
    && chown -R app:app /app/media /app/static

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD curl -f http://localhost:8000/live || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "{{ cookiecutter.package_name }}.main:app", "--host", "0.0.0.0", "--port", "8000"]
