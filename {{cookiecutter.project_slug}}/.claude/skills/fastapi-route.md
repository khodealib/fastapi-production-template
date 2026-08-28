# fastapi-route

Generate a new FastAPI router for a module.

## Usage

When adding a new route to an existing module or creating routes for a new module.

## Instructions

1. Create `modules/{module}/routes.py` with:
   - `from __future__ import annotations`
   - Import `APIRouter`, `Depends`, `Request`, `status` from fastapi
   - Import `Session` from module's deps or `...core.database import get_session`
   - Import schemas from `./schemas`
   - Import use cases from `./service`
   - Import repositories from `./crud`
   - Import envelope helpers from `...core.response`

2. Router setup:
   ```python
   {module}_router = APIRouter(prefix="/{module}", tags=["{module}"])
   ```

3. Define envelope type aliases in `schemas.py`:
   ```python
   from ...core.schemas import Envelope, EnvelopeList

   {SchemaRead}Envelope = Envelope[{SchemaRead}]
   {SchemaRead}ListEnvelope = EnvelopeList[{SchemaRead}]
   ```

4. Route pattern (single resource):
   ```python
   from ...core.response import success_response

   @{module}_router.post("", response_model={SchemaRead}Envelope, status_code=201)
   async def create_item(
       request: Request,
       payload: {SchemaCreate},
       session: Session,
   ) -> {SchemaRead}Envelope:
       repo = {Model}Repository(session)
       item = await Create{Model}(repo).execute(**payload.model_dump())
       return success_response(
           {SchemaRead}.model_validate(item),
           message="{Model} created",
           request=request,
       )
   ```

5. Route pattern (paginated list):
   ```python
   from ...core.response import paginated_response
   from ...core.pagination import PageParams, page_params

   @{module}_router.get("", response_model={SchemaRead}ListEnvelope)
   async def list_items(
       request: Request,
       session: Session,
       params: Annotated[PageParams, Depends(page_params)],
   ) -> {SchemaRead}ListEnvelope:
       repo = {Model}Repository(session)
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

6. Register in `api.py`:
   ```python
   from .modules.{module}.routes import {module}_router
   api_router.include_router({module}_router)
   ```

7. Use `CurrentUser` / `SuperUser` deps for auth:
   ```python
   from .deps import CurrentUser, SuperUser
   ```

8. Add rate limiting if needed:
   ```python
   from ...infrastructure.ratelimit import rate_limit
   limiter = rate_limit("10/hour", key_prefix="{action}")
   @{module}_router.post(..., dependencies=[Depends(limiter)])
   ```

## Conventions

- Routes are thin: parse request → call use case → return envelope response
- No business logic in routes
- Use `Session = Annotated[AsyncSession, Depends(get_session)]` for DB sessions
- Repository instances created per-request: `repo = {Model}Repository(session)`
- Errors propagate from use cases via `AppError` hierarchy
- **All responses use envelope helpers** from `core.response`:
  - `success_response(data, message, request)` — 200/201
  - `paginated_response(items, total, params, message, request)` — 200 list
  - `error_response(exc, request)` — auto-handled by exception handlers
  - `validation_error_response(errors, message, request)` — 422