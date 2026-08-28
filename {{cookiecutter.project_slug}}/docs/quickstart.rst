Quickstart
==========

After installation, you can:

1. **Register a user**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/auth/register \
        -H "Content-Type: application/json" \
        -d '{"email": "user@example.com", "password": "StrongPass1!", "full_name": "Test User"}'

   Response (201):

   .. code-block:: json

      {
        "success": true,
        "data": {
          "id": "uuid",
          "email": "user@example.com",
          "full_name": "Test User",
          "is_active": true,
          "is_superuser": false,
          "created_at": "2024-01-15T10:30:00Z"
        },
        "message": "User registered successfully",
        "errors": null,
        "meta": { "request_id": "...", "pagination": null }
      }

2. **Login**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/auth/token \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=user@example.com&password=StrongPass1!"

   Response (200):

   .. code-block:: json

      {
        "success": true,
        "data": {
          "access_token": "eyJ...",
          "refresh_token": "eyJ...",
          "token_type": "bearer",
          "expires_in": 1800
        },
        "message": "Login successful",
        "errors": null,
        "meta": { "request_id": "...", "pagination": null }
      }

3. **Access protected endpoints**

   .. code-block:: bash

      curl http://localhost:8000/api/users/me \
        -H "Authorization: Bearer <access_token>"

   Response (200):

   .. code-block:: json

      {
        "success": true,
        "data": {
          "id": "uuid",
          "email": "user@example.com",
          "full_name": "Test User",
          "is_active": true,
          "is_superuser": false,
          "created_at": "2024-01-15T10:30:00Z"
        },
        "message": "Current user retrieved",
        "errors": null,
        "meta": { "request_id": "...", "pagination": null }
      }

4. **Check health**

   .. code-block:: bash

      curl http://localhost:8000/health

   Response (200):

   .. code-block:: json

      {
        "success": true,
        "data": {
          "status": "ok",
          "version": "1.0.0",
          "database": "ok"
        },
        "message": "Service is healthy",
        "errors": null,
        "meta": { "request_id": "...", "pagination": null }
      }

5. **List users (superuser only)**

   .. code-block:: bash

      curl http://localhost:8000/api/users \
        -H "Authorization: Bearer <admin_access_token>"

   Response (200):

   .. code-block:: json

      {
        "success": true,
        "data": [
          { "id": "...", "email": "admin@example.com", ... },
          { "id": "...", "email": "user@example.com", ... }
        ],
        "message": "Users retrieved",
        "errors": null,
        "meta": {
          "request_id": "...",
          "pagination": { "page": 1, "size": 20, "total": 2, "pages": 1 }
        }
      }