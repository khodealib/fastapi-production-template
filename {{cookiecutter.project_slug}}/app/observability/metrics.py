"""Prometheus metrics, exposed at ``/metrics``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def setup_metrics(app: FastAPI) -> None:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
