"""Tests for the TaskIQ broker and the tasks registered on it."""

from taskiq import InMemoryBroker

from app.infrastructure.broker import broker
from app.infrastructure.scheduler import scheduler
from app.modules.users.tasks.email import send_email_task


def test_broker_falls_back_to_in_memory_without_redis() -> None:
    """The suite runs with REDIS_URL unset, so no broker process is needed."""
    assert isinstance(broker, InMemoryBroker)


def test_send_email_task_is_registered_on_the_broker() -> None:
    """Importing the task binds it to the single application broker."""
    assert send_email_task.broker is broker
    assert broker.find_task(send_email_task.task_name) is send_email_task


def test_scheduler_uses_the_same_broker() -> None:
    """Scheduled tasks are enqueued onto the broker the worker consumes."""
    assert scheduler.broker is broker
