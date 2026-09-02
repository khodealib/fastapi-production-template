"""The HTTP response contract: envelope schemas, helpers, pagination, OpenAPI.

Deliberately empty of re-exports — ``exceptions.errors`` imports ``http.schemas``
and ``http.openapi`` imports ``exceptions.errors``, so eager re-exports here
would close that loop.
"""
