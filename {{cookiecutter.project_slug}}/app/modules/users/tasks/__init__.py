"""Background tasks for the users module."""

from __future__ import annotations

from .email import send_email_task

__all__ = ["send_email_task"]
