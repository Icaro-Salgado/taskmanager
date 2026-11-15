from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tasks import selectors
from apps.tasks.demo_data import ADMIN_EMAIL, DEMO_PASSWORD, USER_EMAILS
from apps.tasks.models import Status, Task
from apps.tasks.selectors import TaskFilters
from apps.teams import selectors as team_selectors
from apps.teams.models import Membership, Role, Team

pytestmark = pytest.mark.django_db


def seed() -> str:
    out = StringIO()
    call_command("seed_demo", stdout=out)
    return out.getvalue()


def row_counts() -> list[int]:
    return [model.objects.count() for model in (User, Team, Membership, Task)]


def admin_user() -> User:
    return User.objects.get(email=ADMIN_EMAIL)


def test_creates_an_admin_and_users_and_prints_the_demo_credentials() -> None:
    output = seed()

    assert admin_user().is_superuser
    assert admin_user().is_staff
    assert User.objects.filter(email__in=USER_EMAILS, is_superuser=False).count() == len(
        USER_EMAILS
    )
    assert DEMO_PASSWORD in output
    assert "DEMO ONLY" in output


def test_a_seeded_user_can_obtain_a_token(api_client: APIClient) -> None:
    seed()

    response = api_client.post(
        "/api/v1/auth/token",
        {"email": USER_EMAILS[0], "password": DEMO_PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.json()


def test_every_status_is_present_among_the_visible_tasks() -> None:
    seed()

    statuses = {task.status for task in selectors.list_tasks(admin_user(), TaskFilters())}
    archived = {
        task.status for task in selectors.list_tasks(admin_user(), TaskFilters(archived=True))
    }

    assert statuses | archived == set(Status)


def test_the_task_list_has_more_than_one_page_and_some_unassigned_tasks() -> None:
    seed()

    tasks = selectors.list_tasks(
        admin_user(), TaskFilters(team_id=Team.objects.get(name="Platform").pk)
    )

    assert tasks.count() > 20
    assert tasks.filter(assignee__isnull=True).exists()


def test_some_tasks_are_overdue_and_every_overdue_one_is_unfinished() -> None:
    seed()

    overdue = list(selectors.list_tasks(admin_user(), TaskFilters(overdue=True)))

    assert overdue
    assert all(not task.is_terminal for task in overdue)


def test_old_finished_tasks_match_the_archived_filter() -> None:
    seed()

    archived = list(selectors.list_tasks(admin_user(), TaskFilters(archived=True)))

    assert archived
    assert all(task.is_terminal for task in archived)


def test_one_team_has_no_leader_and_one_user_has_a_different_role_in_two_teams() -> None:
    seed()

    teams = team_selectors.active_teams()
    leaderless = [t.name for t in teams if not t.memberships.filter(role=Role.LEADER).exists()]
    ana_roles = set(
        Membership.objects.filter(user__email=USER_EMAILS[0]).values_list("role", flat=True)
    )

    assert leaderless == ["Design Guild"]
    assert ana_roles == {Role.LEADER, Role.MEMBER}


def test_the_soft_deleted_team_and_its_tasks_are_excluded_from_the_selectors() -> None:
    seed()

    legacy = Team.objects.get(name="Legacy Migration")

    assert legacy.deleted_at is not None
    assert legacy.tasks.exists()
    assert legacy not in team_selectors.teams_visible_to(admin_user())
    assert not selectors.tasks_visible_to(admin_user()).filter(team=legacy).exists()


def test_running_the_seed_twice_changes_no_row_counts() -> None:
    seed()
    first = row_counts()

    output = seed()

    assert row_counts() == first
    assert "0 new tasks" in output
