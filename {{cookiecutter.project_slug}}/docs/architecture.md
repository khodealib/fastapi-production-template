# Architecture

## Layout

```text
{{ cookiecutter.package_name }}/
├── api.py                 # central router; carries the global rate limit
├── main.py                # app factory — middleware, admin, error handling
├── middleware.py          # request context, rate-limit headers
├── core/                  # cross-cutting
│   ├── config.py          # pydantic-settings
│   ├── database.py        # async engine, session dependency
│   ├── security.py        # JWT, argon2 hashing
│   ├── schemas.py         # Envelope, EnvelopeList, Pagination
│   ├── response.py        # envelope builders
│   ├── openapi.py         # error documentation derived from exceptions
│   ├── exceptions.py      # AppError hierarchy
│   ├── exception_handlers.py
│   ├── pagination.py
│   ├── net.py             # client identity behind proxies
│   └── health/            # /live, /ready, /health
├── infrastructure/        # cache, email, i18n, ratelimit, tasks
└── modules/
    └── users/
        ├── routes.py      # HTTP layer (thin)
        ├── service.py     # use cases
        ├── crud.py        # repositories
        ├── models.py      # SQLAlchemy ORM
        ├── schemas.py     # Pydantic boundaries
        ├── deps.py        # dependencies, incl. repository providers
        └── admin.py       # SQLAdmin views
```

## Layer rules

Dependencies run one way: `routes → service → crud → models`.

| Layer | Responsibility | Must not |
|---|---|---|
| `routes.py` | Parse, call a use case, return an envelope | Touch the session or hold business logic |
| `service.py` | Use cases — classes with one `execute()` | Import FastAPI |
| `crud.py` | Data access over `AsyncSession` | Hold business rules, or commit |
| `models.py` | ORM entities | — |
| `schemas.py` | The API boundary | Leak ORM objects |

`get_session` commits on success and rolls back on exception, so repositories
`flush()` and never `commit()`.

A module starts as one `service.py` and one `routes.py`. Split into `usecases/`
and `routers/` packages only once they outgrow that — roughly 300 lines or eight
use cases. Never keep both `routes.py` and a `routers/` package: the package
shadows the module and the file silently becomes dead code.

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

## The response envelope

Every `/api` response shares one shape. The client-facing specification lives in
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
registered outside the API prefix and return bare bodies, and they emit `503` as
a plain `JSONResponse` rather than raising — precisely so the envelope exception
handlers cannot re-wrap them. Tests assert the absence of envelope keys.
