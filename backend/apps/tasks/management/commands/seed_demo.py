"""Loads demo data: users, teams, memberships and tasks. Safe to run twice.

Every record is looked up by its natural key (email, team name, team + task title) and only
created when missing, so a second run creates nothing and a demo record someone edited is kept.
Dates are relative to today, so the demo looks right whenever it is first loaded.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.tasks import services
from apps.tasks.demo_data import (
    ADMIN_EMAIL,
    DEMO_PASSWORD,
    TEAMS,
    USER_EMAILS,
    TaskSpec,
    TeamSpec,
)
from apps.tasks.models import TERMINAL_STATUSES, Task
from apps.teams.models import Membership, Role, Team


def _ensure_user(email: str, *, admin: bool = False) -> User:
    user = User.objects.filter(email=email).first()
    if user is not None:
        return user  # keep the password: hashing is slow and the demo may have changed it
    return User.objects.create_user(email, DEMO_PASSWORD, is_staff=admin, is_superuser=admin)


def _ensure_team(spec: TeamSpec, admin: User) -> Team:
    # Straight to the database: there is no create-team service (teams are made in the admin
    # site), and the services cannot produce a team that is already soft-deleted.
    team = Team.objects.filter(name=spec.name, deleted_at__isnull=not spec.deleted).first()
    if team is not None:
        return team
    return Team.objects.create(
        name=spec.name,
        archive_after_days=spec.archive_after_days,
        deleted_at=timezone.now() - timedelta(days=10) if spec.deleted else None,
        deleted_by=admin if spec.deleted else None,
    )


def _ensure_memberships(team: Team, spec: TeamSpec, users: dict[str, User]) -> None:
    # Direct too: `add_member` always grants the member role, and the demo needs leaders.
    for email, role in spec.members.items():
        Membership.objects.get_or_create(team=team, user=users[email], defaults={"role": role})


def _task_author(spec: TeamSpec, users: dict[str, User]) -> User:
    """The leader, or the first member of a team without one."""
    leaders = [email for email, role in spec.members.items() if role == Role.LEADER]
    return users[leaders[0] if leaders else next(iter(spec.members))]


def _ensure_task(
    team: Team, spec: TaskSpec, users: dict[str, User], author: User, *, team_deleted: bool
) -> bool:
    """Creates the task unless it exists. Returns whether it was created."""
    if Task.objects.filter(team=team, title=spec.title).exists():
        return False
    assignee = users[spec.assignee] if spec.assignee else None
    due_date = timezone.localdate() + timedelta(days=spec.due) if spec.due is not None else None
    finished = spec.status in TERMINAL_STATUSES
    if finished or team_deleted:
        # Direct row: the services refuse to create a finished task or to touch a deleted team,
        # and stamp `completed_at` with now, while the demo needs tasks finished long ago.
        Task.objects.create(
            team=team,
            title=spec.title,
            description=spec.description,
            status=spec.status,
            created_by=author,
            assignee=assignee,
            due_date=due_date,
            completed_at=timezone.now() - timedelta(days=spec.finished) if finished else None,
        )
    else:
        services.create_task(
            actor=author,
            team=team,
            title=spec.title,
            description=spec.description,
            status=spec.status,
            assignee_id=assignee.pk if assignee else None,
            due_date=due_date,
        )
    return True


def _seed_team(spec: TeamSpec, users: dict[str, User], admin: User) -> int:
    """Returns the number of tasks created."""
    team = _ensure_team(spec, admin)
    _ensure_memberships(team, spec, users)
    author = _task_author(spec, users)
    created = [
        _ensure_task(team, task, users, author, team_deleted=spec.deleted) for task in spec.tasks
    ]
    return sum(created)


class Command(BaseCommand):
    help = "Create demo users, teams and tasks (demo-only credentials). Safe to run twice."

    @transaction.atomic
    def handle(self, *_args: str, **_options: str) -> None:
        admin = _ensure_user(ADMIN_EMAIL, admin=True)
        users = {email: _ensure_user(email) for email in USER_EMAILS}
        new_tasks = sum(_seed_team(spec, users, admin) for spec in TEAMS)
        self.stdout.write(self.style.SUCCESS(f"Seed done: {new_tasks} new tasks."))
        self.stdout.write("DEMO ONLY credentials (never use outside a local demo):")
        self.stdout.write(f"  admin: {ADMIN_EMAIL}")
        self.stdout.write(f"  users: {', '.join(USER_EMAILS)}")
        self.stdout.write(f"  password for all: {DEMO_PASSWORD}")
