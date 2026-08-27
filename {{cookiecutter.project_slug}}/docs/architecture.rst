Architecture
============

Project layout follows a feature-based module pattern:

.. code-block:: text

   {{ cookiecutter.package_name }}/
   ├── api.py              # Central router
   ├── main.py             # App factory
   ├── middleware.py        # Rate limiting, request context
   ├── core/               # Cross-cutting: config, DB, security
   ├── infrastructure/     # External: cache, email, i18n, tasks
   ├── modules/            # Feature modules
   │   └── users/
   │       ├── routes.py       # HTTP layer (thin)
   │       ├── service.py      # Use cases (business logic)
   │       ├── crud.py         # Repository (data access)
   │       ├── models.py       # SQLAlchemy ORM
   │       ├── schemas.py      # Pydantic boundaries
   │       ├── deps.py         # FastAPI dependencies
   │       └── interactor.py   # Multi-usecase orchestration

Layer rules
-----------

- **Routes** → HTTP only. Parse request, call service, return response.
- **Services** → Use cases. Classes with ``execute()`` method.
- **Crud** → Repositories. Data access, no business logic.
- **Models** → SQLAlchemy ORM entities.
- **Schemas** → Pydantic models for API boundaries.
- **Interactors** → Orchestrate multiple services/repos.

Key patterns
------------

- **Session**: ``Session = Annotated[AsyncSession, Depends(get_session)]``
- **Auth**: ``CurrentUser`` / ``SuperUser`` dependencies from ``deps.py``
- **Errors**: ``AppError`` hierarchy (NotFound, Conflict, Unauthorized)
- **Rate limiting**: ``rate_limit("5/minute", key_prefix="login")``
