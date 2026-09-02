"""OpenTelemetry tracing. Spans go to the console until an exporter is wired."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.sdk.trace import TracerProvider


def build_tracer_provider() -> TracerProvider:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    return provider


def setup_tracing(app: FastAPI) -> TracerProvider:
    """Install the provider globally and instrument the app.

    The returned provider owns the batch processor's background thread — the
    caller must ``shutdown()`` it on lifespan exit.
    """
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    provider = build_tracer_provider()
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    return provider
