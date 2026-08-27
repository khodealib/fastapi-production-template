# fastapi-route

Generate a new FastAPI router for a module.

## Usage

When adding a new route to an existing module or creating routes for a new module.

## Instructions

1. Create `modules/{module}/routes.py` with:
   - `from __future__ import annotations`
   - Import `APIRouter`, `Depends`, `status` from fastapi
   - Import `Session` from module's deps or `...core.database import get_session`
   - Import schemas from `./schemas`
   - Import use cases from `./service`
   - Import repositories from `./crud`

2. Router setup:
   ```python
   {module}_router = APIRouter(prefix="/{module}", tags=["{module}"])
   ```

3. Route pattern:
   ```python
   @{module}_router.get("", response_model=Page[{SchemaRead}])
   async def list_items(
       _: SuperUser,
       session: Session,
       params: Annotated[PageParams, Depends(page_params)],
   ) -> Page[{SchemaRead}]:
       repo = {Model}Repository(session)
       items, total = await List{Models}(repo).execute(
           page=params.page, size=params.size
       )
       return Page.build(
           items=[{SchemaRead}.model_validate(i) for i in items],
           total=total,
           params=params,
       )
   ```

4. Register in `api.py`:
   ```python
   from .modules.{module}.routes import {module}_router
   api_router.include_router({module}_router)
   ```

5. Use `CurrentUser` / `SuperUser` deps for auth:
   ```python
   from .deps import CurrentUser, SuperUser
   ```

6. Add rate limiting if needed:
   ```python
   from ...infrastructure.ratelimit import rate_limit
   limiter = rate_limit("10/hour", key_prefix="{action}")
   @{module}_router.post(..., dependencies=[Depends(limiter)])
   ```

## Conventions

- Routes are thin: parse request → call use case → return response
- No business logic in routes
- Use `Session = Annotated[AsyncSession, Depends(get_session)]` for DB sessions
- Repository instances created per-request: `repo = {Model}Repository(session)`
- Errors propagate from use cases via `AppError` hierarchy
