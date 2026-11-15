from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel
from apps.teams.models import Team


class Status(models.TextChoices):
    TODO = "todo", "To do"
    IN_PROGRESS = "in_progress", "In progress"
    BLOCKED = "blocked", "Blocked"
    DONE = "done", "Done"
    CANCELED = "canceled", "Canceled"


# Finished: read-only except for reopen and delete.
TERMINAL_STATUSES = (Status.DONE, Status.CANCELED)


class Task(TimestampedModel):
    """Soft-deleted like teams. "Archived" is not stored: it is a query condition (selectors)."""

    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tasks"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    overdue_notified_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        constraints = [
            # completed_at is set exactly when the task is finished.
            models.CheckConstraint(
                condition=(
                    models.Q(status__in=TERMINAL_STATUSES, completed_at__isnull=False)
                    | (
                        ~models.Q(status__in=TERMINAL_STATUSES)
                        & models.Q(completed_at__isnull=True)
                    )
                ),
                name="tasks_task_completed_at_matches_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES
