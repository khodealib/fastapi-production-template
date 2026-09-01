Architecture
============

Project layout follows a feature-based module pattern:

.. code-block:: text

   {{ cookiecutter.package_name }}/
   ├── api.py              # Central router
   ├── main.py             # App factory
   ├── middleware.py       # Rate limiting, request context
   ├── core/               # Cross-cutting: config, DB, security
   │   ├── response.py     # Envelope response helpers
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

- **Routes** → HTTP only. Parse request, call service, return envelope response.
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
- **Responses**: Use ``success_response()``, ``paginated_response()``, ``error_response()`` from ``core.response``
- **Request ID**: Available via ``request.state.request_id`` for tracing

API Response Envelope
---------------------

All endpoints return a consistent envelope (see :doc:`quickstart` for examples):

.. code-block:: json

   {
     "success": true,
     "data": {},
     "message": "Operation completed",
     "errors": null,
     "pagination": {...},          // list responses only
     "meta": { "request_id": "..." }
   }

- ``success``: Boolean for easy client-side branching
- ``data``: Payload (object/array) — null on error
- ``message``: Human-readable summary — optional on success, required on error
- ``errors``: Array of ``ErrorDetail`` — null on success
- ``pagination``: Present on list responses only — page, per_page, total,
  total_pages, has_next, has_previous
- ``meta``: Metadata about the request itself (request_id, tracing)

HTTP status codes remain accurate (200, 201, 400, 401, 404, 409, 422, 500).