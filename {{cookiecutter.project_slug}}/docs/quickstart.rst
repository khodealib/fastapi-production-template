Quickstart
==========

After installation, you can:

1. **Register a user**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/auth/register \
        -H "Content-Type: application/json" \
        -d '{"email": "user@example.com", "password": "StrongPass1!", "full_name": "Test User"}'

2. **Login**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/auth/token \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=user@example.com&password=StrongPass1!"

3. **Access protected endpoints**

   .. code-block:: bash

      curl http://localhost:8000/api/users/me \
        -H "Authorization: Bearer <access_token>"

4. **Check health**

   .. code-block:: bash

      curl http://localhost:8000/health
