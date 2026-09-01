"""Celery application + task registry (Django ``CELERY_BEAT_SCHEDULE`` + tasks).

Designed to run without a broker in dev: tasks fall back to eager mode when
``REDIS_URL`` is unset.
"""

from __future__ import annotations

from typing import Any

from celery import Celery

from ..core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "{{ cookiecutter.package_name }}",
    broker=settings.REDIS_URL or "memory://",
    backend=settings.REDIS_URL or "memory://",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={},
)

if settings.REDIS_URL is None:
    celery_app.conf.task_always_eager = True  # dev convenience: no broker needed


@celery_app.task(retries=3, default_retry_delay=60, max_retries=3)
def send_email_task(
    to: str, subject: str, template_name: str, context: dict[str, Any] | None = None
) -> bool:
    """Send an email in the background (smokes Django's EmailMessage flow)."""
    from ..infrastructure.email import send_email

    try:
        send_email(to, subject, template_name, context)
    except Exception as exc:
        raise send_email_task.retry(exc=exc) from exc
    return True
