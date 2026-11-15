"""The only write path for tasks. Every rule on tasks is enforced here, whatever the caller."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import TypedDict

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
)
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.tasks import policies, selectors
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
    task = Task.objects.create(
        team=team,
        title=title,
        description=description,
        status=status,
        created_by=actor,
        assignee=_assignee_for(team, assignee_id),
        due_date=due_date,
    )
    _queue_assignment_notification(actor, task)
    return task


def update_task(*, actor: User, task: Task, changes: TaskChanges) -> Task:
    _ensure_active(task)
    if not policies.can_edit_task(actor, task):
        raise PermissionDeniedError("You may not edit this task.")
    _ensure_not_finished(task)

    if "title" in changes:
        task.title = changes["title"]
    if "description" in changes:
        task.description = changes["description"]
    reassigned = "assignee_id" in changes and changes["assignee_id"] != task.assignee_id
    if reassigned:
        task.assignee = _assignee_for(task.team, changes["assignee_id"])
    if "due_date" in changes and changes["due_date"] != task.due_date:
        task.due_date = changes["due_date"]
        task.overdue_notified_at = None  # a new due date may become overdue again
    if "status" in changes:
        task.status = changes["status"]
        if task.is_terminal:
            task.completed_at = timezone.now()
    task.save()
    if reassigned:
        _queue_assignment_notification(actor, task)
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


def _queue_assignment_notification(actor: User, task: Task) -> None:
    """Queued after the commit, so the worker reads the saved task. Assigning yourself is silent."""
    assignee_id = task.assignee_id
    if assignee_id is None or assignee_id == actor.pk:
        return
    # Imported here: the Celery task module imports this one.
    from apps.tasks.tasks import notify_assignment

    task_id = task.pk
    transaction.on_commit(lambda: notify_assignment.delay(task_id, assignee_id))


def send_assignment_notification(*, task_id: int, assignee_id: int) -> Notification | None:
    """Run by the worker. Sends nothing if the task was deleted or reassigned in the meantime.

    An overdue task says so. Its `overdue_notified_at` is left as it is: a task the daily job has
    already notified is not notified again.
    """
    task = selectors.get_active_task(task_id)
    if task is None or task.assignee is None or task.assignee_id != assignee_id:
        return None
    overdue = ", which is overdue" if selectors.is_overdue(task) else ""
    return create_notification(
        user=task.assignee,
        team=task.team,
        task_id=task.pk,
        message=f'You were assigned task "{task.title}"{overdue}.',
    )


@dataclass(frozen=True)
class OverdueRun:
    notifications: int
    tasks: int


def _overdue_recipients(task: Task, leaders: list[User]) -> list[User]:
    """The assignee and every leader of the team, each once. Admins only as one of those."""
    recipients = {leader.pk: leader for leader in leaders}
    if task.assignee is not None and task.assignee.is_active:
        recipients.setdefault(task.assignee.pk, task.assignee)
    return list(recipients.values())


def _overdue_message(team: Team, tasks: list[Task]) -> tuple[str, int | None]:
    """The message and the task it is about: one task by name, several as a team count."""
    if len(tasks) == 1:
        return f'Task "{tasks[0].title}" is overdue.', tasks[0].pk
    return f'Team "{team.name}" has {len(tasks)} overdue tasks.', None


def notify_overdue_tasks() -> OverdueRun:
    """The daily job: one notification per recipient and team, then the tasks are marked.

    Marked tasks are never picked again, so a second run sends nothing new. A task with nobody to
    notify stays unmarked and is picked up once it has an assignee or a leader.
    """
    with transaction.atomic():
        # Rows locked by a run in progress (beat and the command at once) are skipped, so no task
        # is notified twice.
        tasks = list(
            selectors.overdue_tasks_to_notify(timezone.localdate()).select_for_update(
                skip_locked=True, of=("self",)
            )
        )
        leaders = selectors.active_leaders_by_team({task.team_id for task in tasks})
        groups: dict[tuple[User, Team], list[Task]] = defaultdict(list)
        for task in tasks:
            for user in _overdue_recipients(task, leaders.get(task.team_id, [])):
                groups[(user, task.team)].append(task)
        for (user, team), user_tasks in groups.items():
            message, task_id = _overdue_message(team, user_tasks)
            create_notification(user=user, team=team, message=message, task_id=task_id)
        notified = {task.pk for user_tasks in groups.values() for task in user_tasks}
        Task.objects.filter(pk__in=notified).update(overdue_notified_at=timezone.now())
    return OverdueRun(notifications=len(groups), tasks=len(notified))
