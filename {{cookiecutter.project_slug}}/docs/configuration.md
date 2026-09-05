# Configuration

Every value is read from the environment, or from a `.env` file beside the
project root. Names are case-sensitive and match the attributes on `Settings` in
`app/config/settings.py` exactly — that class is the
source of truth, and this page follows it.

`make init` copies `.env.example` to `.env` to get you started.

## Application

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `{{ cookiecutter.project_name }}` | Shown as the OpenAPI title |
| `APP_VERSION` | `{{ cookiecutter.version }}` | Reported by `/health` and the schema |
| `APP_DESCRIPTION` | project description | OpenAPI description |
| `ENVIRONMENT` | `development` | `development`, `production` or `test`. Outside dev and test the interactive docs are disabled |
| `DEBUG` | `false` | |
| `SECRET_KEY` | dev placeholder | JWT signing key. **The app refuses to start in production while this is the placeholder** |
| `ALLOWED_HOSTS` | `["*"]` | JSON list, enforced by `TrustedHostMiddleware` |
| `CORS_ORIGINS` | `["http://localhost:8000"]` | JSON list |
| `TRUSTED_PROXY_HOPS` | `0` | Reverse proxies in front of the app — see below |

## Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@localhost:5432/{{ cookiecutter.project_slug }}` | Async driver required. `sqlite+aiosqlite:///./dev.db` works for local runs |
| `DB_ECHO` | `false` | Log every statement |

## Auth

| Variable | Default | Description |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |

## Redis, cache and queues

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | unset | Cache, TaskIQ broker and result backend. Unset means the cache no-ops and TaskIQ uses an `InMemoryBroker` (no broker process needed) |
| `CACHE_DEFAULT_TTL_SECONDS` | `300` | |

## Rate limiting

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_STORAGE_URI` | `memory://` | Use Redis in production — in-memory counters are per worker, so N workers give N times the intended limit |
| `RATE_LIMIT_STRATEGY` | `fixed-window` | One of `fixed-window`, `moving-window`, `sliding-window` |
| `RATE_LIMIT_GLOBAL` | `1000/minute` | Applied to every API route as one budget per client |

## Email

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | unset | Unset makes every send a no-op — the default for dev and tests |
| `SMTP_PORT` | `587` | |
| `SMTP_USERNAME` | unset | |
| `SMTP_PASSWORD` | unset | |
| `SMTP_STARTTLS` | `true` | |
| `EMAIL_FROM` | `no-reply@example.com` | |

## i18n and logging

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_LOCALE` | `en` | Fallback when `Accept-Language` matches no compiled catalogue |
| `LOG_JSON` | `false` | Structured JSON output — turn on in production |
| `LOG_LEVEL` | `INFO` | |

## Observability

| Variable | Default | Description |
|---|---|---|
| `ENABLE_METRICS` | `true` | Exposes Prometheus metrics at `/metrics`. The endpoint is unauthenticated — restrict it at the ingress, or turn it off here |
| `ENABLE_TRACING` | `false` | Installs the OpenTelemetry tracer provider and instruments the app. Off by default because the shipped provider exports spans to the console: turn it on once you have wired a real (OTLP) exporter in `app/observability/tracing.py` |

The tracer provider is created in `create_app()` and shut down by the
application lifespan, so the batch export thread is flushed and joined on exit.

## Running behind a proxy

`TRUSTED_PROXY_HOPS` decides whether `X-Forwarded-For` is believed, and it is
security-relevant in both directions.

At `0` the header is ignored entirely and the peer address is used. That is the
right setting when the app is directly exposed: trusting the header there would
let any client rotate it and get a fresh rate-limit budget on every request.

Set it to the exact number of proxies in front of the app — `1` behind a single
nginx, `2` behind nginx plus a load balancer. The value selects that many
entries from the right of the chain, which are the ones your own infrastructure
appended. **Setting it higher than reality makes the value forgeable again**,
because entries further left are supplied by the caller.

The same resolution feeds the rate limiter and the request log, so both agree on
who made a request.
