from datetime import date, datetime

from django.utils import timezone

from apps.accounts.models import User
from apps.tasks.models import TERMINAL_STATUSES, Status, Task
from apps.teams.models import Team


def create_task(
    team: Team,
    created_by: User,
    *,
    title: str = "Task",
    status: Status = Status.TODO,
    assignee: User | None = None,
    due_date: date | None = None,
    completed_at: datetime | None = None,
) -> Task:
    """Test setup straight into the database, bypassing the services under test."""
    if status in TERMINAL_STATUSES and completed_at is None:
        completed_at = timezone.now()
    return Task.objects.create(
        team=team,
        created_by=created_by,
        title=title,
        status=status,
        assignee=assignee,
        due_date=due_date,
        completed_at=completed_at,
    )
