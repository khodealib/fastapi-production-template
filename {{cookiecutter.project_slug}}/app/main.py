"""ASGI entrypoint. The factory lives in :mod:`app.application`."""

from app.application import create_app

app = create_app()
