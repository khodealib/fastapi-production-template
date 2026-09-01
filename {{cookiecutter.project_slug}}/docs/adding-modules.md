# Adding a Module

A module is a feature: everything about `items` lives under
`{{ cookiecutter.package_name }}/modules/items/`. The `users` module is the
worked example — read it alongside this page.

## 1. Create the files

```bash
mkdir -p {{ cookiecutter.package_name }}/modules/items
```

| File | Holds |
|---|---|
| `models.py` | SQLAlchemy ORM entities |
| `schemas.py` | Pydantic request and response schemas |
| `crud.py` | Repositories — data access only |
| `service.py` | Use cases, each a class with `execute()` |
| `routes.py` | The router — thin |
| `deps.py` | Dependencies, including repository providers |
| `admin.py` | SQLAdmin views, if the module needs them |

## 2. Envelope aliases in `schemas.py`

```python
from ...core.schemas import Envelope, EnvelopeList

ItemReadEnvelope = Envelope[ItemRead]
ItemListEnvelope = EnvelopeList[ItemRead]
```

## 3. Repository providers in `deps.py`

Handlers never build a repository themselves.

```python
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from .crud import ItemRepository

Session = Annotated[AsyncSession, Depends(get_session)]


def get_item_repository(session: Session) -> ItemRepository:
    return ItemRepository(session)


ItemRepo = Annotated[ItemRepository, Depends(get_item_repository)]
```

## 4. The router

Declare the errors each route can raise. `error_responses` reads them off the
exception classes, so the documentation cannot drift from the behaviour. Do not
re-declare `RateLimitedError` — it arrives from the parent router.

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...core.exceptions import ConflictError, NotFoundError
from ...core.openapi import error_responses
from ...core.pagination import PageParams, page_params
from ...core.response import paginated_response, success_response
from .deps import ItemRepo
from .schemas import ItemCreate, ItemListEnvelope, ItemRead, ItemReadEnvelope
from .service import CreateItem, ListItems

item_router = APIRouter(prefix="/items", tags=["items"])


@item_router.get(
    "",
    response_model=ItemListEnvelope,
    responses=error_responses(validation=True),
)
async def list_items(
    request: Request,
    repo: ItemRepo,
    params: Annotated[PageParams, Depends(page_params)],
) -> ItemListEnvelope:
    items, total = await ListItems(repo).execute(
        page=params.page, page_size=params.page_size
    )
    return paginated_response(
        items=[ItemRead.model_validate(i) for i in items],
        total=total,
        params=params,
        message="Items retrieved",
        request=request,
    )


@item_router.post(
    "",
    response_model=ItemReadEnvelope,
    status_code=201,
    responses=error_responses(ConflictError, validation=True),
)
async def create_item(
    request: Request,
    payload: ItemCreate,
    repo: ItemRepo,
) -> ItemReadEnvelope:
    item = await CreateItem(repo).execute(**payload.model_dump())
    return success_response(
        ItemRead.model_validate(item),
        message="Item created",
        request=request,
    )
```

## 5. Register it

```python
# api.py
from .modules.items.routes import item_router

api_router.include_router(item_router)
```

## 6. Make the tables real

Alembic only sees models that have been imported, so add the module to
`{{ cookiecutter.package_name }}/alembic/env.py`:

```python
from {{ cookiecutter.package_name }}.modules.items import models as _items_models  # noqa: F401
```

Then:

```bash
make makemigrations m="add items module"
make migrate
```

Forgetting the import produces an empty migration rather than an error — check
the generated file before applying it.

## 7. Test it

Add `tests/test_items.py`. Assert on the envelope, not just the status:

```python
body = resp.json()
assert body["success"] is True
assert body["data"]["title"] == "…"
assert body["pagination"]["has_next"] is False   # list responses
```

## 8. Verify

```bash
make verify        # ruff + mypy --strict + bandit + pytest
```
