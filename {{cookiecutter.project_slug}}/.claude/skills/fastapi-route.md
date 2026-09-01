# fastapi-route

Generate a new FastAPI router for a module.

## Usage

When adding a new route to an existing module or creating routes for a new module.

## Instructions

1. Create `modules/{module}/routes.py` with:
   - `from __future__ import annotations`
   - Import `APIRouter`, `Depends`, `Request`, `status` from fastapi
   - Import the repository deps from `./deps` (never build a repository inline)
   - Import schemas from `./schemas`
   - Import use cases from `./service`
   - Import envelope helpers from `...core.response`
   - Import `error_responses` from `...core.openapi`

2. Add repository providers to `modules/{module}/deps.py`:
   ```python
   def get_{module}_repository(session: Session) -> {Model}Repository:
       return {Model}Repository(session)

   {Model}Repo = Annotated[{Model}Repository, Depends(get_{module}_repository)]
   ```

3. Router setup — errors every route shares go on the router:
   ```python
   {module}_router = APIRouter(
       prefix="/{module}",
       tags=["{module}"],
       responses=error_responses(UnauthorizedError),
   )
   ```

4. Define envelope type aliases in `schemas.py`:
   ```python
   from ...core.schemas import Envelope, EnvelopeList

   {SchemaRead}Envelope = Envelope[{SchemaRead}]
   {SchemaRead}ListEnvelope = EnvelopeList[{SchemaRead}]
   ```

5. Route pattern (single resource) — document the errors it can raise:
   ```python
   from ...core.response import success_response

   @{module}_router.post(
       "",
       response_model={SchemaRead}Envelope,
       status_code=201,
       responses=error_responses(ConflictError, validation=True),
   )
   async def create_item(
       request: Request,
       payload: {SchemaCreate},
       repo: {Model}Repo,
   ) -> {SchemaRead}Envelope:
       item = await Create{Model}(repo).execute(**payload.model_dump())
       return success_response(
           {SchemaRead}.model_validate(item),
           message="{Model} created",
           request=request,
       )
   ```

6. Route pattern (paginated list):
   ```python
   from ...core.response import paginated_response
   from ...core.pagination import PageParams, page_params

   @{module}_router.get(
       "",
       response_model={SchemaRead}ListEnvelope,
       responses=error_responses(ForbiddenError, validation=True),
   )
   async def list_items(
       request: Request,
       repo: {Model}Repo,
       params: Annotated[PageParams, Depends(page_params)],
   ) -> {SchemaRead}ListEnvelope:
       items, total = await List{Models}(repo).execute(
           page=params.page, size=params.size
       )
       return paginated_response(
           items=[{SchemaRead}.model_validate(i) for i in items],
           total=total,
           params=params,
           message="{Models} retrieved",
           request=request,
       )
   ```

7. Register in `api.py`:
   ```python
   from .modules.{module}.routes import {module}_router
   api_router.include_router({module}_router)
   ```

8. Use `CurrentUser` / `SuperUser` deps for auth:
   ```python
   from .deps import CurrentUser, SuperUser
   ```

9. Rate limiting: every `/api` route already inherits the global budget from
   `api_router`, so 429 is documented for free. Add a dependency only where a
   route needs a tighter limit, optionally with its own algorithm:
   ```python
   from ...infrastructure.ratelimit import RateLimitStrategy, rate_limit

   limiter = rate_limit(
       "10/hour",
       strategy=RateLimitStrategy.MOVING_WINDOW,  # optional per-route override
       key_prefix="{action}",
   )

   @{module}_router.post(..., dependencies=[Depends(limiter)])
   ```
   Do not re-declare `RateLimitedError` in `responses` — it arrives from the
   parent router.

## Conventions

- Routes are thin: parse request → call use case → return envelope response
- No business logic in routes
- Repositories arrive as dependencies (`{Model}Repo`), never built in a handler
- Errors propagate from use cases via the `AppError` hierarchy
- **Every route declares the errors it can raise** via
  `responses=error_responses(...)`, passing the exception classes themselves.
  Add `validation=True` wherever a body, path or query parameter can fail
  validation. Never document the success response a second time —
  `response_model` already defines it, and a duplicate is how docs drift
- **All responses use envelope helpers** from `core.response`:
  - `success_response(data, message, request)` — 200/201
  - `paginated_response(items, total, params, message, request)` — 200 list
  - `error_response(exc, request)` — auto-handled by exception handlers
  - `validation_error_response(errors, message, request)` — 422

## When to split

Keep all routes in `routes.py` until it passes roughly 300 lines. Past that,
turn it into a `routers/` package with one file per route and re-export from
`__init__.py`. Never keep both `routes.py` and a `routers/` package in one
module — the package shadows the module and the file silently becomes dead
code.
