# API Response Contract

Everything a client needs to consume this API without reading the server code.
It is stable: the shapes here change only in a release that says so.

The live schema is always at `/openapi.json`, with an interactive browser at
`/docs`. This page explains the parts a generated client cannot tell you — what
the fields mean and what to do about them.

## The envelope

Every response under the API — success or failure — has the same top level.

```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "errors": null,
  "meta": { "request_id": "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c" }
}
```

| Field | Type | Notes |
|---|---|---|
| `success` | boolean | `true` on 2xx, `false` otherwise. Branch on this, not on the shape of `data` |
| `data` | object \| array \| null | The payload. `null` on every error |
| `message` | string \| null | Human-readable. Safe to show a user on error; on success it is a confirmation, not a label |
| `errors` | array \| null | Populated only on error. `null` on success |
| `pagination` | object | **List responses only.** Absent on single resources |
| `meta` | object | Facts about the request, not the payload |

Two rules worth internalising:

- **`data` is never partially valid.** If `success` is `false`, `data` is `null`
  — there is no half-succeeded response to defend against.
- **The HTTP status is authoritative.** `success` mirrors it for convenience.
  If they ever disagree, trust the status code.

## Reading a list

List endpoints put pagination at the top level, beside `data` — not inside
`meta`, because it describes the payload rather than the request.

```json
{
  "success": true,
  "data": [ { "id": "…" }, { "id": "…" } ],
  "message": "Users retrieved",
  "errors": null,
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 245,
    "total_pages": 13,
    "has_next": true,
    "has_previous": false
  },
  "meta": { "request_id": "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c" }
}
```

Request a page with the `page` and `page_size` query parameters — the same names
you get back, so nothing needs translating:

```
GET /users?page=2&page_size=50
```

`page` starts at 1. `page_size` is capped at 100; asking for more is a 422, not
a silent clamp. Use `has_next` for "load more" rather than comparing
`page < total_pages` yourself — it stays correct if the rules change.

## Reading an error

```json
{
  "success": false,
  "data": null,
  "message": "A user with this email already exists.",
  "errors": [
    {
      "code": "conflict",
      "message": "A user with this email already exists.",
      "field": null,
      "data": null
    }
  ],
  "meta": { "request_id": "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c" }
}
```

| Field | Notes |
|---|---|
| `code` | **Branch on this, never on `message`.** Stable machine identifier |
| `message` | Human-readable. May be reworded at any time |
| `field` | Dotted path to the offending input on a validation error — `body.email`, `query.page`. `null` when the error is not about one field |
| `data` | Extra context for this specific error, or `null`. Shape depends on `code` |

`errors` is an array because validation reports every problem at once. Other
errors carry exactly one entry.

### Error codes

| Code | Status | When | What the client should do |
|---|---|---|---|
| `validation_error` | 422 | A field failed schema validation | Show the message against `field` |
| `bad_request` | 400 | Malformed request the schema cannot describe | Fix the request; retrying unchanged will not help |
| `unauthorized` | 401 | Missing, malformed, or expired credentials | Refresh the token once, then send the user to sign in |
| `forbidden` | 403 | Authenticated, but not allowed | Do not retry. Hide the action instead of surfacing a failure |
| `not_found` | 404 | The resource does not exist | Do not retry |
| `conflict` | 409 | Collides with existing state, e.g. a duplicate email | Show the message; the user must change something |
| `rate_limited` | 429 | Too many requests | Back off — see below |
| `internal_error` | 500 | Unhandled server fault | Retry with backoff, and quote `request_id` when reporting it |

A `422` from a request body looks like this — note one entry per bad field:

```json
{
  "success": false,
  "data": null,
  "message": "Validation failed",
  "errors": [
    { "code": "validation_error", "message": "Field required", "field": "body.email" },
    { "code": "validation_error", "message": "String should have at least 8 characters", "field": "body.password" }
  ],
  "meta": { "request_id": "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c" }
}
```

## Rate limiting

Every endpoint is rate limited. Successful responses carry the current budget:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1788256620
```

`X-RateLimit-Reset` is a Unix timestamp in seconds. When a request is refused
you get `429` with a `rate_limited` error and a `Retry-After` header:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 59
```

```json
{
  "success": false,
  "data": null,
  "message": "Too many requests, slow down.",
  "errors": [
    { "code": "rate_limited", "message": "Too many requests, slow down.",
      "field": null, "data": { "retry_after": 59 } }
  ],
  "meta": { "request_id": "3f1a9c2e7b8d4f5a9e0c1b2d3a4f5e6c" }
}
```

Wait `Retry-After` seconds before retrying. Do not retry immediately on 429 —
the limiter counts the retry too. Sign-in is limited far more tightly than
reading, so a login form should disable its submit button while a request is in
flight.

## Health probes are not enveloped

`/live`, `/ready` and `/health` sit outside the API prefix and answer with bare
bodies, because Kubernetes reads them, not your client:

```json
{ "status": "healthy",
  "checks": { "database": { "status": "ok", "detail": null } },
  "version": "1.0.0" }
```

They return `503` with the same shape when a dependency is down. Do not send
them through your envelope parser.

### `GET /metrics`

Prometheus text format, and likewise outside the envelope. It is absent from
`/openapi.json` on purpose — it is an operational endpoint, not part of the API.

Alongside the HTTP series, each module exports its own business counters. The
`users` module publishes:

| Metric | Labels | Meaning |
|---|---|---|
| `user_registrations_total` | — | accounts created |
| `user_authentication_attempts_total` | `outcome` = `success` \| `failure` | login attempts |
| `token_refresh_total` | `outcome` = `success` \| `failure` | refresh-token rotations |

Unauthenticated by default: restrict it at the load balancer or ingress in
production, or set `ENABLE_METRICS=false` to disable it entirely.

## Conventions across every endpoint

**Timestamps** are ISO 8601 in UTC with an explicit offset:
`2026-09-01T09:28:05.583Z`. Never a local time, never a bare naive string.

**Identifiers** are UUIDs as strings.

**Field names** are `snake_case`, in requests and responses alike.

**`meta.request_id`** is echoed in the `X-Request-ID` response header and
written to the server log for that request. Include it in a bug report and the
exact request can be found. You may also *send* `X-Request-ID` yourself to
correlate a client trace with the server's.

**Absent versus null**: a `null` field is present and empty; an absent field
means that concept does not apply to this response — `pagination` on a single
resource is absent, not `null`.

## Authentication

Get a token pair from `POST /auth/token`, form-encoded, not JSON:

```
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=StrongPass1!
```

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ…",
    "refresh_token": "eyJ…",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "Login successful",
  "errors": null,
  "meta": { "request_id": "…" }
}
```

The field is `username` because the endpoint follows the OAuth2 password form;
its value is the user's email.

Send the access token on every subsequent request:

```
Authorization: Bearer eyJ…
```

`expires_in` is seconds. When the access token expires, exchange the refresh
token at `POST /auth/refresh` — this one takes JSON:

```json
{ "refresh_token": "eyJ…" }
```

**Refresh tokens rotate.** Every refresh returns a new pair and revokes the one
you sent, so a refresh token is single-use. Store the new pair immediately and
never retry a refresh with a token you already spent — the second attempt
returns `401` with `unauthorized`, and the correct response is to sign in again.
Serialise refreshes: if several requests 401 at once, one refresh should run and
the rest should wait for it, or they will revoke each other's tokens.

## Generating a client

The schema at `/openapi.json` is complete: every endpoint documents the errors
it can raise, with an example body per error code, and `Retry-After` on the
429s. Generate a typed client from it rather than hand-writing one.

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/schema.d.ts
```

Note that a generated client gives you types, not behaviour. Refresh rotation,
`Retry-After` backoff and error-code branching are yours to implement — this
page is the specification for them.
