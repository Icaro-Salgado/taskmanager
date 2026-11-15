"""The only write path for tasks. Every rule on tasks is enforced here, whatever the caller."""

from datetime import date
from typing import TypedDict

from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
)
from apps.tasks import policies
from apps.tasks.models import TERMINAL_STATUSES, Status, Task
from apps.teams.models import Membership, Team


class TaskChanges(TypedDict, total=False):
    """Fields an update may change. A missing key means "leave as is"; None clears the value."""

    title: str
    description: str
    status: Status
    assignee_id: int | None
    due_date: date | None


def _ensure_active(task: Task) -> None:
    if task.deleted_at is not None or task.team.deleted_at is not None:
        raise NotFoundError("Task not found.")


def _ensure_not_finished(task: Task) -> None:
    if task.is_terminal:
        raise RuleViolationError(
            "Finished tasks are read-only. Reopen the task first.", code="task_finished"
        )


def _assignee_for(team: Team, user_id: int | None) -> User | None:
    """The invariant: an assignee is an active member of the task's team."""
    if user_id is None:
        return None
    membership = (
        Membership.objects.select_related("user")
        .filter(team=team, user_id=user_id, user__is_active=True)
        .first()
    )
    if membership is None:
        raise RuleViolationError(
            "The assignee must be an active member of the team.", code="invalid_assignee"
        )
    return membership.user


def create_task(
    *,
    actor: User,
    team: Team,
    title: str,
    description: str = "",
    status: Status = Status.TODO,
    assignee_id: int | None = None,
    due_date: date | None = None,
) -> Task:
    if team.deleted_at is not None:
        raise NotFoundError("Team not found.")
    if not policies.can_create_task(actor, team):
        raise PermissionDeniedError("Only team members can create tasks.")
    if status in TERMINAL_STATUSES:
        raise RuleViolationError(
            "A task cannot be created as done or canceled.", code="terminal_on_create"
        )
    return Task.objects.create(
        team=team,
        title=title,
        description=description,
        status=status,
        created_by=actor,
        assignee=_assignee_for(team, assignee_id),
        due_date=due_date,
    )


def update_task(*, actor: User, task: Task, changes: TaskChanges) -> Task:
    _ensure_active(task)
    if not policies.can_edit_task(actor, task):
        raise PermissionDeniedError("You may not edit this task.")
    _ensure_not_finished(task)

    if "title" in changes:
        task.title = changes["title"]
    if "description" in changes:
        task.description = changes["description"]
    if "assignee_id" in changes and changes["assignee_id"] != task.assignee_id:
        task.assignee = _assignee_for(task.team, changes["assignee_id"])
    if "due_date" in changes and changes["due_date"] != task.due_date:
        task.due_date = changes["due_date"]
        task.overdue_notified_at = None  # a new due date may become overdue again
    if "status" in changes:
        task.status = changes["status"]
        if task.is_terminal:
            task.completed_at = timezone.now()
    task.save()
    return task


def reopen_task(*, actor: User, task: Task) -> Task:
    """Moves a finished task back to in progress. Allowed for whoever may edit it."""
    _ensure_active(task)
    if not policies.can_edit_task(actor, task):
        raise PermissionDeniedError("You may not reopen this task.")
    if not task.is_terminal:
        raise RuleViolationError("Only finished tasks can be reopened.", code="task_not_finished")
    task.status = Status.IN_PROGRESS
    task.completed_at = None
    task.overdue_notified_at = None
    task.save(update_fields=["status", "completed_at", "overdue_notified_at", "updated_at"])
    return task


def assign_self(*, actor: User, task: Task) -> Task:
    """A member takes an unassigned task. Changes nothing else."""
    _ensure_active(task)
    if not policies.can_assign_self(actor, task):
        raise PermissionDeniedError("Only team members can take tasks.")
    _ensure_not_finished(task)
    if task.assignee_id is not None:
        raise ConflictError("This task is already assigned.", code="already_assigned")
    task.assignee = actor
    task.save(update_fields=["assignee", "updated_at"])
    return task


def delete_task(*, actor: User, task: Task) -> None:
    """Soft delete, allowed even for finished tasks."""
    _ensure_active(task)
    if not policies.can_delete_task(actor, task):
        raise PermissionDeniedError("You may not delete this task.")
    task.deleted_at = timezone.now()
    task.deleted_by = actor
    task.save(update_fields=["deleted_at", "deleted_by", "updated_at"])


def unassign_member_tasks(*, team: Team, user: User) -> int:
    """Called by teams when a member leaves, inside the same transaction.

    Covers deleted tasks too, so restoring one never brings back a non-member assignee.
    """
    return Task.objects.filter(team=team, assignee=user).update(
        assignee=None, updated_at=timezone.now()
    )
