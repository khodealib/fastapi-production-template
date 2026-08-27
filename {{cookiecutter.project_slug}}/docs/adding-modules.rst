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

3. Register the router in ``api.py``:

   .. code-block:: python

      from .modules.{module_name}.routes import {module_name}_router
      api_router.include_router({module_name}_router)

4. Generate a migration:

   .. code-block:: bash

      make makemigrations m="add {module_name} module"

5. Apply the migration:

   .. code-block:: bash

      make migrate

6. Add tests in ``tests/test_{module_name}.py``.
