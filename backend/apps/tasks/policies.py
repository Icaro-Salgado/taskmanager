"""Who may do what on a task. Only current members (and admins) have rights on a team's tasks.

The `*_with_role` functions take the user's role in the task's team as an argument: the task
serializer answers them for every task of a page from the role the selectors annotate, instead of
one query per task.
"""

from apps.accounts.models import User
from apps.tasks.models import Task
from apps.teams.models import Role, Team
from apps.teams.policies import is_admin
from apps.teams.selectors import role_in


def can_create_task(user: User, team: Team) -> bool:
    return is_admin(user) or role_in(team, user) is not None


def can_edit_task(user: User, task: Task) -> bool:
    """Creator, assignee, team leader or admin. Also governs reopen."""
    return can_edit_task_with_role(user, task, role_in(task.team, user))


def can_edit_task_with_role(user: User, task: Task, role: Role | None) -> bool:
    if is_admin(user):
        return True
    if role is None:
        return False
    return role == Role.LEADER or user.pk in (task.created_by_id, task.assignee_id)


def can_delete_task(user: User, task: Task) -> bool:
    """Creator, team leader or admin."""
    return can_delete_task_with_role(user, task, role_in(task.team, user))


def can_delete_task_with_role(user: User, task: Task, role: Role | None) -> bool:
    if is_admin(user):
        return True
    if role is None:
        return False
    return role == Role.LEADER or user.pk == task.created_by_id


def can_assign_self(user: User, task: Task) -> bool:
    """Any team member. Admins who are not members cannot: an assignee must be a member."""
    return role_in(task.team, user) is not None
