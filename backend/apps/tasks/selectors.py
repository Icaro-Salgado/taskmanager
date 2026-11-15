"""Read queries for tasks.

Deleted tasks and tasks of deleted teams are excluded here explicitly. "Overdue" and "archived" are
defined once, as query conditions, and the API reads them from these annotations.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db.models import (
    BooleanField,
    DateTimeField,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
    Value,
)
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.tasks.models import TERMINAL_STATUSES, Status, Task


def overdue_condition(today: date) -> Q:
    """Due before today (in TIME_ZONE) and not finished.

    `due_date IS NOT NULL` is explicit: without it a task with no due date compares to NULL, and
    the annotation would be NULL instead of False.
    """
    return Q(due_date__isnull=False, due_date__lt=today) & ~Q(status__in=TERMINAL_STATUSES)


def archived_condition(now: datetime) -> Q:
    """Finished longer ago than the team's `archive_after_days`."""
    archive_age = ExpressionWrapper(
        F("team__archive_after_days") * Value(timedelta(days=1)), output_field=DurationField()
    )
    cutoff = ExpressionWrapper(Value(now) - archive_age, output_field=DateTimeField())
    return Q(status__in=TERMINAL_STATUSES, completed_at__lt=cutoff)


def tasks_visible_to(user: User) -> QuerySet[Task]:
    """Tasks of the active teams the user belongs to (every active team for an admin)."""
    tasks = Task.objects.filter(deleted_at__isnull=True, team__deleted_at__isnull=True)
    if not user.is_superuser:
        tasks = tasks.filter(team__memberships__user=user)
    is_overdue = ExpressionWrapper(
        overdue_condition(timezone.localdate()), output_field=BooleanField()
    )
    return tasks.select_related("team", "assignee", "created_by").annotate(is_overdue=is_overdue)


def get_visible_task(user: User, task_id: int) -> Task:
    try:
        return tasks_visible_to(user).get(pk=task_id)
    except Task.DoesNotExist as exc:
        raise NotFoundError("Task not found.") from exc


@dataclass(frozen=True)
class TaskFilters:
    team_id: int | None = None
    status: Status | None = None
    due_after: date | None = None
    due_before: date | None = None
    assignee_id: int | None = None
    unassigned: bool = False
    overdue: bool | None = None
    archived: bool = False


def list_tasks(user: User, filters: TaskFilters) -> QuerySet[Task]:
    """The task list, soonest due date first (no date last), then by id.

    Archived tasks are left out unless `archived` is set, which returns only them.
    """
    tasks = tasks_visible_to(user)
    archived = archived_condition(timezone.now())
    tasks = tasks.filter(archived) if filters.archived else tasks.exclude(archived)
    if filters.team_id is not None:
        tasks = tasks.filter(team_id=filters.team_id)
    if filters.status is not None:
        tasks = tasks.filter(status=filters.status)
    if filters.due_after is not None:
        tasks = tasks.filter(due_date__gte=filters.due_after)
    if filters.due_before is not None:
        tasks = tasks.filter(due_date__lte=filters.due_before)
    if filters.assignee_id is not None:
        tasks = tasks.filter(assignee_id=filters.assignee_id)
    if filters.unassigned:
        tasks = tasks.filter(assignee__isnull=True)
    if filters.overdue is not None:
        overdue = overdue_condition(timezone.localdate())
        tasks = tasks.filter(overdue) if filters.overdue else tasks.exclude(overdue)
    return tasks.order_by(F("due_date").asc(nulls_last=True), "id")
