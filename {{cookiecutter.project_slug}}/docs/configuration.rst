Configuration
=============

All configuration is via environment variables (or ``.env`` file).

Core
----

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``SECRET_KEY``
     - (required)
     - JWT signing key (min 32 chars)
   * - ``DATABASE_URL``
     - ``sqlite+aiosqlite:///./dev.db``
     - Async database URL
   * - ``REDIS_URL``
     - (optional)
     - Redis URL for cache/rate-limiting
   * - ``ENVIRONMENT``
     - ``development``
     - ``development`` / ``production`` / ``test``

Auth
----

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``ACCESS_TOKEN_EXPIRE_MINUTES``
     - ``30``
     - Access token TTL
   * - ``REFRESH_TOKEN_EXPIRE_DAYS``
     - ``7``
     - Refresh token TTL

Email
-----

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``SMTP_HOST``
     - (optional)
     - SMTP server host
   * - ``SMTP_PORT``
     - ``587``
     - SMTP server port
   * - ``SMTP_USER``
     - (optional)
     - SMTP username
   * - ``SMTP_PASSWORD``
     - (optional)
     - SMTP password
   * - ``EMAIL_FROM``
     - ``noreply@example.com``
     - Sender address

Celery
------

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``CELERY_BROKER_URL``
     - ``redis://localhost:6379/0``
     - Celery broker URL
   * - ``CELERY_RESULT_BACKEND``
     - ``redis://localhost:6379/1``
     - Celery result backend

Rate Limiting
-------------

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``RATE_LIMIT_STORAGE_URI``
     - (optional)
     - Redis URI for rate limiting
   * - ``RATE_LIMIT_DEFAULT``
     - ``100/minute``
     - Default rate limit
