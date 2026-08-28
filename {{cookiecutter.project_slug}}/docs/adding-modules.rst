Adding Modules
==============

1. Create the module directory:

   .. code-block:: bash

      mkdir -p {{ cookiecutter.package_name }}/modules/{module_name}

2. Create the required files:

   - ``models.py`` — SQLAlchemy ORM models
   - ``schemas.py`` — Pydantic request/response schemas
   - ``crud.py`` — Repository for data access
   - ``service.py`` — Use case classes with ``execute()``
   - ``routes.py`` — FastAPI router (thin HTTP layer)
   - ``deps.py`` — FastAPI dependencies
   - ``interactor.py`` — (optional) Multi-usecase orchestration

3. Define envelope type aliases in ``schemas.py``:

   .. code-block:: python

      from ...core.schemas import Envelope, EnvelopeList

      ItemReadEnvelope = Envelope[ItemRead]
      ItemListEnvelope = EnvelopeList[ItemRead]

4. Use envelope helpers in ``routes.py``:

   .. code-block:: python

      from fastapi import APIRouter, Request, Depends
      from ...core.database import get_session
      from ...core.pagination import PageParams, page_params
      from ...core.response import success_response, paginated_response
      from .schemas import ItemReadEnvelope, ItemListEnvelope

      item_router = APIRouter(prefix="/items", tags=["items"])

      @item_router.get("", response_model=ItemListEnvelope)
      async def list_items(
          request: Request,
          session: Session,
          params: Annotated[PageParams, Depends(page_params)],
      ) -> ItemListEnvelope:
          repo = ItemRepository(session)
          items, total = await ListItems(repo).execute(
              page=params.page, size=params.size
          )
          return paginated_response(
              items=[ItemRead.model_validate(i) for i in items],
              total=total,
              params=params,
              message="Items retrieved",
              request=request,
          )

      @item_router.post("", response_model=ItemReadEnvelope, status_code=201)
      async def create_item(
          request: Request,
          payload: ItemCreate,
          session: Session,
      ) -> ItemReadEnvelope:
          repo = ItemRepository(session)
          item = await CreateItem(repo).execute(**payload.model_dump())
          return success_response(
              ItemRead.model_validate(item),
              message="Item created",
              request=request,
          )

5. Register the router in ``api.py``:

   .. code-block:: python

      from .modules.{module_name}.routes import {module_name}_router
      api_router.include_router({module_name}_router)

6. Generate a migration:

   .. code-block:: bash

      make makemigrations m="add {module_name} module"

7. Apply the migration:

   .. code-block:: bash

      make migrate

8. Add tests in ``tests/test_{module_name}.py`` following envelope assertions.