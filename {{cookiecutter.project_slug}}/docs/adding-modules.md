# Adding a Module

A module is a feature: everything about `items` lives under
`app/modules/items/`. The `users` module is the worked example — read it
alongside this page.

## 1. Create the packages

```bash
mkdir -p app/modules/items/{models,schemas,repositories,usecases,routes,events}
```

| Package or file | Holds |
|---|---|
| `models/` | SQLAlchemy ORM entities, one per file |
| `schemas/` | Pydantic request and response schemas |
| `repositories/` | Repositories — data access only, one per entity |
| `usecases/` | Use cases, one class with `execute()` per file |
| `routes/` | The routers — thin, one per file |
| `deps.py` | Dependencies, including repository providers |
| `admin.py` | SQLAdmin views, if the module needs them |
| `metrics.py` | Prometheus counters for this module's business events |
| `tasks/` | TaskIQ background tasks (`@broker.task`) |
| `crons/` | TaskIQ scheduled tasks — `@broker.task` with a `schedule` label |
| `events/` | Signal names (`__init__.py`) and async handlers (`handlers.py`) |

Every package gets an `__init__.py` that re-exports its public names, so callers
write `from ..usecases import CreateItem` and never reach into a file directly.
Names are spelled out in full — `repositories/`, not `crud/`.

**Imports follow the module boundary.** Inside `modules/items/` the imports are
relative (`from ..deps import ItemRepo`); anything outside it is absolute
(`from app.http.response import success_response`). A `from ...` is always a
mistake — it means the import left the module and should have been absolute.

## 2. Envelope aliases in `schemas/item.py`

```python
from app.http.schemas import Envelope, EnvelopeList

ItemReadEnvelope = Envelope[ItemRead]
ItemListEnvelope = EnvelopeList[ItemRead]
```

## 3. Repository providers in `deps.py`

Handlers never build a repository themselves.

```python
from typing import Annotated

from fastapi import Depends

from app.database.session import Session

from .repositories import ItemRepository


def get_item_repository(session: Session) -> ItemRepository:
    return ItemRepository(session)


ItemRepo = Annotated[ItemRepository, Depends(get_item_repository)]
```

## 4. Business metrics in `metrics.py`

Named Prometheus metrics for the events this module cares about. Use cases call
them; routes and repositories do not — HTTP-level instrumentation already lives
in `observability/metrics.py`.

```python
from prometheus_client import Counter

items_created_total = Counter(
    "items_created_total",
    "Total number of items created.",
)
```

Then, in the use case, after the state change has actually happened:

```python
from ..metrics import items_created_total


class CreateItem:
    async def execute(self, ...) -> Item:
        item = await self.repo.create(...)
        items_created_total.inc()
        return item
```

Metrics with an `outcome` label (`["outcome"]`) are worth it wherever a use case
can fail for a business reason: increment `outcome="failure"` before *every*
`raise` and `outcome="success"` before the return, or the ratio lies.

The same use case can also announce the change on the in-process event bus, so
unrelated code can react without the use case knowing about it. Signal names go
in `events/__init__.py`, handlers in `events/handlers.py`:

```python
# events/__init__.py
ITEM_CREATED = "items.created"

# events/handlers.py
from app.events import subscribe

from . import ITEM_CREATED


@subscribe(ITEM_CREATED)
async def on_item_created(item_id: str) -> None:
    ...
```

```python
# usecases/create_item.py
from app.events import bus

from ..events import ITEM_CREATED

items_created_total.inc()
await bus.publish(ITEM_CREATED, item_id=str(item.id))
```

Handlers subscribe at import time, so `application.py` must import
`app.modules.items.events.handlers` for its side effect. They run concurrently
inside the publishing request and a raising handler is logged rather than
propagated — work that must outlive the response belongs in `tasks/` instead.

## 5. The router — `routes/items.py`

Declare the errors each route can raise. `error_responses` reads them off the
exception classes, so the documentation cannot drift from the behaviour. Do not
re-declare `RateLimitedError` — it arrives from the parent router.

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.exceptions.errors import ConflictError, NotFoundError
from app.http.openapi import error_responses
from app.http.pagination import PageParams, page_params
from app.http.response import paginated_response, success_response

from ..deps import ItemRepo
from ..schemas import ItemCreate, ItemListEnvelope, ItemRead, ItemReadEnvelope
from ..usecases import CreateItem, ListItems

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

Re-export it from `routes/__init__.py`:

```python
from .items import item_router

__all__ = ["item_router"]
```

## 6. Register it

```python
# api.py
from app.modules.items.routes import item_router

api_router.include_router(item_router)
```

It mounts at the root — `/items`. There is no `/api` prefix.

## 7. Make the tables real

Alembic only sees models that have been imported, so add the module to
`app/alembic/env.py` — one line per entity:

```python
from app.modules.items.models import Item as _Item  # noqa: F401
```

Then:

```bash
make makemigrations m="add items module"
make migrate
```

Forgetting the import produces an empty migration rather than an error — check
the generated file before applying it.

## 8. Test it

Add `tests/test_items.py`. Assert on the envelope, not just the status:

```python
body = resp.json()
assert body["success"] is True
assert body["data"]["title"] == "…"
assert body["pagination"]["has_next"] is False   # list responses
```

## 9. Verify

```bash
make verify        # ruff + mypy --strict + bandit + pytest
```
