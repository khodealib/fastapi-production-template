# Architecture

## Layout

The Python package is always `app/` — it does not take the project's name.

```text
app/
├── api.py                 # central router; carries the global rate limit
├── main.py                # ASGI entrypoint: `app = create_app()`
├── application.py         # app factory — middleware, admin, error handling
├── config/
│   ├── settings.py        # pydantic-settings
│   └── constants.py       # Environment enum
├── database/
│   ├── base.py            # DeclarativeBase + naming convention
│   ├── engine.py          # async engine, dispose_engine
│   └── session.py         # SessionFactory, get_session, Session
├── security/
│   ├── jwt.py             # token issuing and decoding
│   ├── passwords.py       # argon2 hashing
│   └── constants.py       # token type / scheme discriminators
├── exceptions/
│   ├── errors.py          # AppError hierarchy
│   └── handlers.py        # envelope-rendering handlers
├── http/                  # the response contract
│   ├── schemas.py         # Envelope, EnvelopeList, Pagination
│   ├── response.py        # envelope builders
│   ├── pagination.py      # Page, page_params
│   ├── openapi.py         # error documentation derived from exceptions
│   └── net.py             # client identity behind proxies
├── middleware/
│   ├── request_context.py # request id + structured request log
│   └── rate_limit_headers.py
├── observability/
│   ├── logging.py         # structlog configuration
│   ├── metrics.py         # Prometheus, exposed at /metrics
│   └── tracing.py         # OpenTelemetry
├── events/                # bus.py — in-process async EventBus + subscribe
├── health/                # /live, /ready, /health
├── utils/                 # datetime.py (utcnow) and other small shared helpers
├── infrastructure/        # admin_auth, broker, scheduler, cache, email,
│                       #   i18n, ratelimit
└── modules/
    └── users/
        ├── routes/        # HTTP layer (thin), one router per file
        ├── usecases/      # use cases, one class per file
        ├── repositories/  # repositories, one per entity
        ├── models/        # SQLAlchemy ORM, one entity per file
        ├── schemas/       # Pydantic boundaries
        ├── deps.py        # dependencies, incl. repository providers
        ├── metrics.py     # Prometheus counters for this module's events
        ├── tasks/         # TaskIQ background tasks
        ├── crons/         # TaskIQ scheduled tasks (cron schedules)
        ├── events/        # signal names + async handlers on the event bus
        └── admin.py       # SQLAdmin views
```

Names are spelled out in full: `database/` not `db/`, `repositories/` not
`crud/`, `usecases/` not `services/`. The only abbreviations are the
well-established ones — `http`, `jwt`, `api`.

The `modules/<name>/` directory is also the import boundary: imports inside a
module are relative (`from ..repositories import ItemRepository`), imports that
leave it are absolute (`from app.security.jwt import decode_token`). A `from
...` is never correct — it means the import escaped the module.

## Layer rules

Dependencies run one way: `routes → usecases → repositories → models`.

| Layer | Responsibility | Must not |
|---|---|---|
| `routes/` | Parse, call a use case, return an envelope | Touch the session or hold business logic |
| `usecases/` | Use cases — classes with one `execute()` | Import FastAPI |
| `repositories/` | Data access over `AsyncSession` | Hold business rules, or commit |
| `models/` | ORM entities | — |
| `schemas/` | The API boundary | Leak ORM objects |

`get_session` commits on success and rolls back on exception, so repositories
`flush()` and never `commit()`.

Every layer is a package from the first file: one use case per file in
`usecases/`, one router per file in `routes/`, one entity per file in `models/`,
each re-exported from the package's `__init__.py`. A module does not grow into
this layout — it starts there.

## Key patterns

- **Repositories arrive as dependencies** — `UserRepo`, `RefreshTokenRepo` from
  the module's `deps.py`. Never constructed inside a handler.
- **Auth** — `CurrentUser` and `SuperUser` dependencies.
- **Errors** — raise from the `AppError` hierarchy; the registered handlers
  render the envelope. Never return an error yourself.
- **Error documentation** — `responses=error_responses(NotFoundError, …)` reads
  the status code, error code, description and headers off the exception classes,
  so the schema cannot drift from behaviour. There is deliberately no equivalent
  helper for success responses: `response_model` is their only source of truth.
- **Rate limiting** — layered. `api_router` carries an app-wide budget per
  client; a route adds its own stricter `rate_limit(...)` when it needs one, and
  the narrower limit owns the `X-RateLimit-*` headers.
- **Request ID** — `request.state.request_id`, echoed as `X-Request-ID`.
- **Business metrics** — each module owns a `metrics.py` of named Prometheus
  metrics; its use cases increment them after a state change or on each error
  path. They surface on `/metrics` alongside the HTTP series that
  `observability/metrics.py` collects.
- **Events** — `app/events` is an in-process async bus, the Django-signal
  equivalent. A use case publishes after a successful side effect
  (`await bus.publish(USER_REGISTERED, ...)`); a module's `events/handlers.py`
  subscribes with `@subscribe(...)` and `application.py` imports it so the
  handlers exist before the first request. Handlers run concurrently inside the
  publishing request and a raising one is logged, not propagated — anything that
  must outlive the response belongs in `tasks/` as a TaskIQ task instead.

## The response envelope

Every API response shares one shape. The client-facing specification lives in
[API Contract](api-contract.md); this is the server-side view.

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed",
  "errors": null,
  "pagination": { },
  "meta": { "request_id": "…" }
}
```

- `pagination` is a top-level member of `EnvelopeList` only — it describes the
  payload, so it does not belong in `meta`.
- `meta` holds facts about the request itself.
- HTTP status codes stay accurate; `success` mirrors them for convenience.

**The health probes are the one exception.** `/live`, `/ready` and `/health` are
registered before the module routers and return bare bodies, and they emit `503` as
a plain `JSONResponse` rather than raising — precisely so the envelope exception
handlers cannot re-wrap them. Tests assert the absence of envelope keys.
