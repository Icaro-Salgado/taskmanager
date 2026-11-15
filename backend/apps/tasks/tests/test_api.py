from collections.abc import Callable
from datetime import timedelta

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import client_for, create_user
from apps.tasks.models import Status, Task
from apps.tasks.tests.factories import create_task
from apps.teams.tests.factories import TeamScenario, add_membership, create_team

TASKS_URL = "/api/v1/tasks"


def task_url(task: Task, action: str = "") -> str:
    return f"{TASKS_URL}/{task.pk}" + (f"/{action}" if action else "")


def test_tasks_require_authentication(api_client: APIClient) -> None:
    assert api_client.get(TASKS_URL).status_code == 401


def test_create_returns_the_task_with_its_computed_fields(scenario: TeamScenario) -> None:
    yesterday = timezone.localdate() - timedelta(days=1)

    response = client_for(scenario.member).post(
        TASKS_URL,
        {
            "team": scenario.team.pk,
            "title": "Ship it",
            "assignee": scenario.leader.pk,
            "due_date": yesterday.isoformat(),
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Ship it"
    assert body["status"] == "todo"
    assert body["assignee"] == {"id": scenario.leader.pk, "email": "leader@example.com"}
    assert body["created_by"]["email"] == "member@example.com"
    assert (body["is_overdue"], body["completed_at"]) == (True, None)


def test_creating_in_a_team_the_user_cannot_see_answers_404(scenario: TeamScenario) -> None:
    response = client_for(scenario.outsider).post(
        TASKS_URL, {"team": scenario.team.pk, "title": "Sneaky"}, format="json"
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"title": ""}, "invalid"),
        ({"title": "T", "status": "archived"}, "invalid"),
        ({"title": "T", "status": "done"}, "terminal_on_create"),
        ({"title": "T", "assignee": 999999}, "invalid_assignee"),
    ],
)
def test_invalid_creations_answer_400(
    scenario: TeamScenario, payload: dict[str, object], code: str
) -> None:
    response = client_for(scenario.member).post(
        TASKS_URL, {"team": scenario.team.pk, **payload}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["code"] == code


def test_a_task_of_another_team_answers_404(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)

    response = client_for(scenario.outsider).get(task_url(task))

    assert response.status_code == 404


def test_read_and_edit_every_field(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)
    client = client_for(scenario.leader)
    due = (timezone.localdate() + timedelta(days=7)).isoformat()

    client.patch(task_url(task), {"description": "Details", "due_date": due}, format="json")
    body = client.get(task_url(task)).json()

    assert (body["description"], body["due_date"], body["is_overdue"]) == ("Details", due, False)


def test_patch_changes_only_the_fields_sent(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member, title="Old", assignee=scenario.leader)

    response = client_for(scenario.member).patch(
        task_url(task), {"status": "in_progress", "assignee": None}, format="json"
    )

    body = response.json()
    assert (body["title"], body["status"], body["assignee"]) == ("Old", "in_progress", None)


def test_a_member_who_may_not_edit_gets_403(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.leader)

    response = client_for(scenario.member).patch(task_url(task), {"title": "X"}, format="json")

    assert response.status_code == 403


def test_the_team_of_a_task_cannot_change(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)
    beta = create_team("Beta")

    response = client_for(scenario.leader).patch(task_url(task), {"team": beta.pk}, format="json")

    assert response.status_code == 400
    assert "team" in response.json()["details"]


def test_finishing_then_editing_then_reopening(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)
    client = client_for(scenario.member)

    done = client.patch(task_url(task), {"status": "done"}, format="json").json()
    blocked = client.patch(task_url(task), {"title": "Too late"}, format="json")
    reopened = client.post(task_url(task, "reopen")).json()

    assert done["completed_at"] is not None
    assert (blocked.status_code, blocked.json()["code"]) == (400, "task_finished")
    assert (reopened["status"], reopened["completed_at"]) == ("in_progress", None)


def test_assign_self(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.leader)
    client = client_for(scenario.member)

    taken = client.post(task_url(task, "assign-self"))
    again = client.post(task_url(task, "assign-self"))

    assert taken.json()["assignee"]["email"] == "member@example.com"
    assert (again.status_code, again.json()["code"]) == (409, "already_assigned")


def test_delete_hides_the_task(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)
    client = client_for(scenario.member)

    assert client.delete(task_url(task)).status_code == 204
    assert client.get(task_url(task)).status_code == 404


def test_the_list_is_paginated_with_a_maximum_page_size(scenario: TeamScenario) -> None:
    for index in range(3):
        create_task(scenario.team, scenario.member, title=f"T{index}")
    client = client_for(scenario.member)

    page = client.get(TASKS_URL, {"page_size": 2}).json()
    clamped = client.get(TASKS_URL, {"page_size": 1000})

    assert (page["count"], len(page["results"]), page["next"] is not None) == (3, 2, True)
    assert clamped.status_code == 200


def test_list_filters_are_read_from_the_query_string(scenario: TeamScenario) -> None:
    create_task(scenario.team, scenario.member, title="Free")
    create_task(scenario.team, scenario.member, title="Taken", assignee=scenario.member)
    finished = timezone.now() - timedelta(days=60)
    create_task(
        scenario.team, scenario.member, title="Old", status=Status.DONE, completed_at=finished
    )
    client = client_for(scenario.member)

    def titles(params: dict[str, str]) -> list[str]:
        return [task["title"] for task in client.get(TASKS_URL, params).json()["results"]]

    assert titles({"assignee": "none"}) == ["Free"]
    assert titles({"assignee": str(scenario.member.pk), "status": "todo"}) == ["Taken"]
    assert titles({"archived": "true"}) == ["Old"]
    assert titles({"overdue": "false", "team": str(scenario.team.pk)}) == ["Free", "Taken"]


@pytest.mark.parametrize(
    "params",
    [
        {"assignee": "me"},
        # A digit for str.isdigit() that int() refuses: it must be a 400, not a server error.
        {"assignee": "²"},
        {"due_after": "yesterday"},
        {"status": "archived"},
    ],
)
def test_invalid_filters_answer_400(scenario: TeamScenario, params: dict[str, str]) -> None:
    response = client_for(scenario.member).get(TASKS_URL, params)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid"


def count_queries(action: Callable[[], object]) -> int:
    with CaptureQueriesContext(connection) as queries:
        action()
    return len(queries)


@pytest.mark.parametrize("viewer", ["member", "leader", "admin"])
def test_list_queries_do_not_grow_with_the_number_of_tasks(
    scenario: TeamScenario, viewer: str
) -> None:
    client = client_for(getattr(scenario, viewer))
    create_task(scenario.team, scenario.member, assignee=scenario.leader)
    few = count_queries(lambda: client.get(TASKS_URL))
    for index in range(10):
        user = create_user(f"u{index}@example.com")
        add_membership(scenario.team, user)
        create_task(scenario.team, user, assignee=user)

    many = count_queries(lambda: client.get(TASKS_URL))
    first = client.get(TASKS_URL).json()["results"][0]

    # One count for the pagination, one page with its related rows and the viewer's role, which
    # answers can_edit and can_delete for every task.
    assert many == few == 2
    assert {"can_edit", "can_delete"} <= first.keys()


def test_each_task_says_what_the_caller_may_do(scenario: TeamScenario) -> None:
    assignee = create_user("assignee@example.com")
    other = create_user("other@example.com")
    add_membership(scenario.team, assignee)
    add_membership(scenario.team, other)
    task = create_task(scenario.team, scenario.member, assignee=assignee)
    viewers = {
        "creator": scenario.member,
        "assignee": assignee,
        "other member": other,
        "leader": scenario.leader,
        "admin (not a member)": scenario.admin,
    }

    def allowed(body: dict[str, object]) -> tuple[object, object]:
        return body["can_edit"], body["can_delete"]

    detail = {
        name: allowed(client_for(user).get(task_url(task)).json()) for name, user in viewers.items()
    }
    listed = {
        name: allowed(client_for(user).get(TASKS_URL).json()["results"][0])
        for name, user in viewers.items()
    }

    expected = {
        "creator": (True, True),
        "assignee": (True, False),
        "other member": (False, False),
        "leader": (True, True),
        "admin (not a member)": (True, True),
    }
    assert detail == listed == expected


def test_mutations_answer_the_permissions_of_the_caller(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.leader)

    taken = client_for(scenario.member).post(task_url(task, "assign-self")).json()

    # Taking the task makes the member its assignee: they may now edit it, not delete it.
    assert (taken["can_edit"], taken["can_delete"]) == (True, False)


def test_tasks_are_read_only_in_the_admin_site(scenario: TeamScenario) -> None:
    task = create_task(scenario.team, scenario.member)
    admin_site = Client()
    admin_site.force_login(scenario.admin)

    assert admin_site.get("/admin/tasks/task/").status_code == 200
    assert admin_site.get(f"/admin/tasks/task/{task.pk}/change/").status_code == 200
    assert admin_site.post(f"/admin/tasks/task/{task.pk}/change/", {}).status_code == 403
    assert admin_site.get("/admin/tasks/task/add/").status_code == 403
    assert admin_site.get(f"/admin/tasks/task/{task.pk}/delete/").status_code == 403
