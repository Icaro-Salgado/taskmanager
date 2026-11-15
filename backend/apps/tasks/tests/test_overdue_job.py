from datetime import date, timedelta
from io import StringIO

import pytest
from celery.schedules import crontab
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.tests.factories import create_user
from apps.notifications.models import Notification
from apps.tasks import services, tasks
from apps.tasks.models import Status, Task
from apps.tasks.services import OverdueRun
from apps.tasks.tests.factories import create_task
from apps.teams.models import Role
from apps.teams.tests.factories import TeamScenario, add_membership, create_team
from config.celery import app as celery_app
from config.env import env_time


def yesterday() -> date:
    return timezone.localdate() - timedelta(days=1)


def overdue_task(
    scenario: TeamScenario, title: str = "Late", *, assignee: User | None = None
) -> Task:
    return create_task(
        scenario.team, scenario.member, title=title, assignee=assignee, due_date=yesterday()
    )


def received(user: User) -> list[tuple[str, int | None]]:
    return [(n.message, n.task_id) for n in Notification.objects.filter(user=user).order_by("id")]


def test_one_overdue_task_notifies_the_assignee_and_the_leaders(scenario: TeamScenario) -> None:
    task = overdue_task(scenario, assignee=scenario.member)

    run = services.notify_overdue_tasks()

    expected = [('Task "Late" is overdue.', task.pk)]
    assert received(scenario.member) == received(scenario.leader) == expected
    assert run == OverdueRun(notifications=2, tasks=1)
    task.refresh_from_db()
    assert task.overdue_notified_at is not None


def test_several_overdue_tasks_make_one_team_notification(scenario: TeamScenario) -> None:
    mine = overdue_task(scenario, "Mine", assignee=scenario.member)
    overdue_task(scenario, "Nobody's")

    services.notify_overdue_tasks()

    assert received(scenario.leader) == [('Team "Alpha" has 2 overdue tasks.', None)]
    assert received(scenario.member) == [('Task "Mine" is overdue.', mine.pk)]


def test_a_second_run_sends_nothing_new(scenario: TeamScenario) -> None:
    overdue_task(scenario, assignee=scenario.member)
    services.notify_overdue_tasks()

    run = services.notify_overdue_tasks()

    assert run == OverdueRun(notifications=0, tasks=0)
    assert Notification.objects.count() == 2


def test_tasks_are_grouped_per_team(scenario: TeamScenario) -> None:
    other_team = create_team("Beta")
    add_membership(other_team, scenario.leader, Role.LEADER)
    first = overdue_task(scenario, "First")
    second = create_task(other_team, scenario.leader, title="Second", due_date=yesterday())

    services.notify_overdue_tasks()

    assert received(scenario.leader) == [
        ('Task "First" is overdue.', first.pk),
        ('Task "Second" is overdue.', second.pk),
    ]


def test_a_leader_who_is_the_assignee_is_notified_once(scenario: TeamScenario) -> None:
    overdue_task(scenario, assignee=scenario.leader)

    run = services.notify_overdue_tasks()

    assert run.notifications == 1
    assert len(received(scenario.leader)) == 1


def test_admins_are_notified_only_as_assignee_or_leader(scenario: TeamScenario) -> None:
    overdue_task(scenario)
    services.notify_overdue_tasks()
    assert received(scenario.admin) == []

    add_membership(scenario.team, scenario.admin, Role.LEADER)
    later = overdue_task(scenario, "Later")
    services.notify_overdue_tasks()

    assert received(scenario.admin) == [('Task "Later" is overdue.', later.pk)]


def test_a_task_with_nobody_to_notify_stays_unmarked_until_someone_exists(db: None) -> None:
    team = create_team("Orphan")
    creator = create_user("creator@example.com")
    add_membership(team, creator)
    task = create_task(team, creator, due_date=yesterday())

    first = services.notify_overdue_tasks()
    task.refresh_from_db()
    assert first == OverdueRun(notifications=0, tasks=0)
    assert task.overdue_notified_at is None

    add_membership(team, create_user("new-leader@example.com"), Role.LEADER)
    second = services.notify_overdue_tasks()

    assert second == OverdueRun(notifications=1, tasks=1)


def test_deactivated_users_are_not_recipients(scenario: TeamScenario) -> None:
    task = overdue_task(scenario, assignee=scenario.member)
    User.objects.filter(pk__in=[scenario.member.pk, scenario.leader.pk]).update(is_active=False)

    run = services.notify_overdue_tasks()

    task.refresh_from_db()
    assert run == OverdueRun(notifications=0, tasks=0)
    assert task.overdue_notified_at is None  # picked up again once someone is active


def test_deleted_tasks_and_tasks_of_deleted_teams_are_ignored(scenario: TeamScenario) -> None:
    deleted = overdue_task(scenario, "Deleted")
    Task.objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())
    other_team = create_team("Gone")
    add_membership(other_team, scenario.leader, Role.LEADER)
    in_deleted_team = create_task(other_team, scenario.leader, due_date=yesterday())
    other_team.deleted_at = timezone.now()
    other_team.save()

    run = services.notify_overdue_tasks()

    assert run == OverdueRun(notifications=0, tasks=0)
    assert not Task.objects.filter(
        pk__in=[deleted.pk, in_deleted_team.pk], overdue_notified_at__isnull=False
    ).exists()


@pytest.mark.parametrize(
    ("due_in_days", "status"),
    [(0, Status.TODO), (3, Status.TODO), (None, Status.TODO), (-1, Status.DONE)],
)
def test_tasks_that_are_not_overdue_are_ignored(
    scenario: TeamScenario, due_in_days: int | None, status: Status
) -> None:
    due_date = None if due_in_days is None else timezone.localdate() + timedelta(due_in_days)
    create_task(scenario.team, scenario.member, status=status, due_date=due_date)

    assert services.notify_overdue_tasks() == OverdueRun(notifications=0, tasks=0)


def test_a_new_due_date_makes_the_task_notifiable_again(scenario: TeamScenario) -> None:
    task = overdue_task(scenario, assignee=scenario.member)
    services.notify_overdue_tasks()

    services.update_task(
        actor=scenario.leader,
        task=task,
        changes={"due_date": timezone.localdate() - timedelta(days=2)},
    )

    assert services.notify_overdue_tasks().tasks == 1


def test_the_command_runs_the_job_on_demand(scenario: TeamScenario) -> None:
    overdue_task(scenario, assignee=scenario.member)
    out = StringIO()

    call_command("notify_overdue", stdout=out)

    assert out.getvalue().strip() == "Sent 2 notification(s) about 1 overdue task(s)."


def test_the_celery_task_runs_the_job(scenario: TeamScenario) -> None:
    overdue_task(scenario, assignee=scenario.member)

    assert tasks.notify_overdue_tasks.delay().get() == 2


def test_beat_schedules_the_job_daily_at_the_configured_time() -> None:
    entry = settings.CELERY_BEAT_SCHEDULE["notify-overdue-tasks"]

    assert entry["task"] in celery_app.tasks
    assert entry["task"] == tasks.notify_overdue_tasks.name
    at = env_time("OVERDUE_JOB_TIME", "08:00")
    assert entry["schedule"] == crontab(hour=at.hour, minute=at.minute)
