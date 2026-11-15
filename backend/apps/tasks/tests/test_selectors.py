from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import create_user
from apps.core.exceptions import NotFoundError
from apps.tasks import selectors, services
from apps.tasks.models import Status, Task
from apps.tasks.selectors import TaskFilters
from apps.tasks.serializers import TaskSerializer
from apps.tasks.tests.factories import create_task
from apps.teams import services as team_services
from apps.teams.tests.factories import TeamScenario, add_membership, create_team


def listed(scenario: TeamScenario, filters: TaskFilters | None = None) -> list[str]:
    """Titles of the task list as the team leader sees it."""
    tasks = selectors.list_tasks(scenario.leader, filters or TaskFilters())
    return [task.title for task in tasks]


# --- Visibility -------------------------------------------------------------------------------


def test_members_see_their_teams_tasks_and_admins_see_all(scenario: TeamScenario) -> None:
    create_task(scenario.team, scenario.member, title="Ours")
    beta = create_team("Beta")
    create_task(beta, scenario.admin, title="Theirs")

    member_view = [t.title for t in selectors.tasks_visible_to(scenario.member)]
    admin_view = sorted(t.title for t in selectors.tasks_visible_to(scenario.admin))
    outsider_view = list(selectors.tasks_visible_to(scenario.outsider))

    assert (member_view, admin_view, outsider_view) == (["Ours"], ["Ours", "Theirs"], [])


def test_deleted_tasks_and_tasks_of_deleted_teams_are_hidden(scenario: TeamScenario) -> None:
    gone = create_task(scenario.team, scenario.member, title="Gone")
    Task.objects.filter(pk=gone.pk).update(deleted_at=timezone.now())
    beta = create_team("Beta")
    create_task(beta, scenario.admin, title="In a deleted team")
    team_services.delete_team(actor=scenario.admin, team=beta)

    assert list(selectors.tasks_visible_to(scenario.admin)) == []
    with pytest.raises(NotFoundError):
        selectors.get_visible_task(scenario.admin, gone.pk)


def test_a_task_in_another_team_is_not_found(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)

    with pytest.raises(NotFoundError):
        selectors.get_visible_task(scenario.outsider, task.pk)


# --- Overdue ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("days_from_today", "status", "expected"),
    [
        (-1, Status.TODO, True),
        (-1, Status.BLOCKED, True),
        (0, Status.TODO, False),  # due today is not overdue yet
        (1, Status.IN_PROGRESS, False),
        (-1, Status.DONE, False),  # finished tasks are never overdue
        (-1, Status.CANCELED, False),
        (None, Status.TODO, False),  # no due date
    ],
)
def test_is_overdue(
    scenario: TeamScenario, days_from_today: int | None, status: Status, expected: bool
) -> None:
    due = None if days_from_today is None else timezone.localdate() + timedelta(days_from_today)
    task = create_task(scenario.team, scenario.member, status=status, due_date=due)

    assert (
        TaskSerializer(selectors.get_visible_task(scenario.member, task.pk)).data["is_overdue"]
        is expected
    )


def test_today_is_taken_in_the_configured_time_zone(scenario: TeamScenario) -> None:
    # 01:30 UTC on 10 March is still 22:30 on 9 March in Sao Paulo (UTC-3).
    late_evening = datetime(2026, 3, 10, 1, 30, tzinfo=UTC)
    task = create_task(scenario.team, scenario.member, due_date=date(2026, 3, 9))

    with patch("django.utils.timezone.now", return_value=late_evening):
        found = selectors.get_visible_task(scenario.member, task.pk)

    assert TaskSerializer(found).data["is_overdue"] is False


# --- Archived ---------------------------------------------------------------------------------


def finished_days_ago(scenario: TeamScenario, title: str, days: int) -> Task:
    completed = timezone.now() - timedelta(days=days)
    return create_task(
        scenario.team, scenario.member, title=title, status=Status.DONE, completed_at=completed
    )


def test_archived_tasks_leave_the_list_and_only_the_archived_filter_returns_them(
    scenario: TeamScenario,
) -> None:
    create_task(scenario.team, scenario.member, title="Open")
    finished_days_ago(scenario, "Recent", days=14)
    finished_days_ago(scenario, "Old", days=16)  # the team archives after 15 days

    assert listed(scenario) == ["Open", "Recent"]
    assert listed(scenario, TaskFilters(archived=True)) == ["Old"]


def test_each_team_has_its_own_archive_age(scenario: TeamScenario) -> None:
    scenario.team.archive_after_days = 30
    scenario.team.save()
    finished_days_ago(scenario, "Sixteen days", days=16)

    assert listed(scenario, TaskFilters(archived=True)) == []


def test_a_reopened_task_is_no_longer_archived(scenario: TeamScenario) -> None:
    old = finished_days_ago(scenario, "Old", days=40)
    services.reopen_task(actor=scenario.leader, task=old)

    assert listed(scenario) == ["Old"]


# --- Ordering and filters ---------------------------------------------------------------------


def test_order_is_soonest_due_first_then_no_date_then_by_id(scenario: TeamScenario) -> None:
    today = timezone.localdate()
    create_task(scenario.team, scenario.member, title="No date A")
    create_task(scenario.team, scenario.member, title="Later", due_date=today + timedelta(5))
    create_task(scenario.team, scenario.member, title="No date B")
    create_task(scenario.team, scenario.member, title="Sooner", due_date=today + timedelta(1))

    assert listed(scenario) == ["Sooner", "Later", "No date A", "No date B"]


def test_filters(scenario: TeamScenario) -> None:
    today = timezone.localdate()
    other = create_user("other@example.com")
    add_membership(scenario.team, other)
    create_task(scenario.team, scenario.member, title="Late", due_date=today - timedelta(2))
    create_task(
        scenario.team,
        scenario.member,
        title="Mine",
        status=Status.BLOCKED,
        assignee=other,
        due_date=today + timedelta(3),
    )
    create_task(scenario.team, scenario.member, title="Far", due_date=today + timedelta(30))
    beta = create_team("Beta")
    add_membership(beta, scenario.leader)
    create_task(beta, scenario.leader, title="Beta task")

    assert listed(scenario, TaskFilters(team_id=beta.pk)) == ["Beta task"]
    assert listed(scenario, TaskFilters(status=Status.BLOCKED)) == ["Mine"]
    assert listed(
        scenario, TaskFilters(due_after=today - timedelta(2), due_before=today + timedelta(3))
    ) == [
        "Late",
        "Mine",
    ]
    assert listed(scenario, TaskFilters(assignee_id=other.pk)) == ["Mine"]
    assert listed(scenario, TaskFilters(unassigned=True)) == ["Late", "Far", "Beta task"]
    assert listed(scenario, TaskFilters(overdue=True)) == ["Late"]
    assert listed(scenario, TaskFilters(overdue=False)) == ["Mine", "Far", "Beta task"]
