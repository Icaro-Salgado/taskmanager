"""Celery tasks of the tasks app: thin entry points, the rules live in the services."""

from celery import shared_task

from apps.tasks import services


@shared_task
def notify_overdue_tasks() -> int:
    """Queued daily by beat (CELERY_BEAT_SCHEDULE). Returns how many notifications were sent."""
    return services.notify_overdue_tasks().notifications


@shared_task
def notify_assignment(task_id: int, assignee_id: int) -> None:
    services.send_assignment_notification(task_id=task_id, assignee_id=assignee_id)
