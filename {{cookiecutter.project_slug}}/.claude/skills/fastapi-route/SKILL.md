---
name: fastapi-route
description: Scaffold or extend a module's FastAPI router: thin handlers, envelope responses, errors documented from the exception classes with error_responses, repositories injected via deps.py, per-route rate limits. Use when adding a route or creating the routes/ package for a new module.
---

# fastapi-route

Generate a new FastAPI router for a module.

## Instructions

1. Create `modules/{module}/routes/{resource}.py` with:
   - `from __future__ import annotations`
   - Import `APIRouter`, `Depends`, `Request`, `status` from fastapi
   - Import the repository deps from `..deps` (never build a repository inline)
   - Import schemas from `..schemas`
   - Import use cases from `..usecases`
   - Import envelope helpers from `app.http.response`
   - Import `error_responses` from `app.http.openapi`
   - Re-export the router from `modules/{module}/routes/__init__.py`

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

4. Define envelope type aliases in `schemas/{resource}.py`:
   ```python
   from app.http.schemas import Envelope, EnvelopeList

   {SchemaRead}Envelope = Envelope[{SchemaRead}]
   {SchemaRead}ListEnvelope = EnvelopeList[{SchemaRead}]
   ```

5. Route pattern (single resource) — document the errors it can raise:
   ```python
   from app.http.response import success_response

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
   from app.http.pagination import PageParams, page_params
   from app.http.response import paginated_response

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
           page=params.page, page_size=params.page_size
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
   from ..deps import CurrentUser, SuperUser
   ```

9. Rate limiting: every API route already inherits the global budget from
   `api_router`, so 429 is documented for free. Add a dependency only where a
   route needs a tighter limit, optionally with its own algorithm:
   ```python
   from app.infrastructure.ratelimit import RateLimitStrategy, rate_limit

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

- Thin handler: parse the request, call one use case, return an envelope helper.
  No business logic, no session access, no repository built inline — repositories
  arrive as `{Model}Repo` from `deps.py`
- Errors propagate from use cases as `AppError` subclasses; raise, never return
- **Every route declares the errors it can raise** via
  `responses=error_responses(...)`, passing the exception classes themselves.
  Add `validation=True` wherever a body, path or query parameter can fail
  validation. Errors shared by a whole router go on the router. Never document
  the success shape a second time — `response_model` is its only source of
  truth, and a duplicate is how docs drift
- Envelope helpers from `http.response`:
  - `success_response(data, message, request)` — 200/201
  - `paginated_response(items, total, params, message, request)` — 200 list
  - `error_response(exc, request)` — raised, rendered by the exception handlers
  - `validation_error_response(errors, message, request)` — 422

## One file per router

`routes/` is a package from the first route — there is no threshold to cross and
no `routes.py` to grow out of. Give each resource or concern its own file
(`auth.py`, `users.py`) holding exactly one `APIRouter`, and re-export every
router from `routes/__init__.py`.
