from collections.abc import Callable

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import client_for, create_user
from apps.teams import services
from apps.teams.models import Membership, Role
from apps.teams.tests.factories import TeamScenario, add_membership, create_team


def members_url(scenario: TeamScenario, user: User | None = None) -> str:
    base = f"/api/v1/teams/{scenario.team.pk}/members"
    return f"{base}/{user.pk}" if user else base


def test_team_endpoints_require_authentication(api_client: APIClient) -> None:
    assert api_client.get("/api/v1/teams").status_code == 401


def test_members_see_their_teams_with_their_role(scenario: TeamScenario) -> None:
    create_team("Hidden")

    response = client_for(scenario.member).get("/api/v1/teams")

    assert response.json() == [
        {"id": scenario.team.pk, "name": "Alpha", "archive_after_days": 15, "my_role": "member"}
    ]


def test_admins_see_every_active_team(scenario: TeamScenario) -> None:
    create_team("Beta")
    gone = create_team("Gone")
    services.delete_team(actor=scenario.admin, team=gone)

    response = client_for(scenario.admin).get("/api/v1/teams")

    assert [(t["name"], t["my_role"]) for t in response.json()] == [
        ("Alpha", None),
        ("Beta", None),
    ]


def test_members_read_a_team(scenario: TeamScenario) -> None:
    response = client_for(scenario.leader).get(f"/api/v1/teams/{scenario.team.pk}")

    assert response.json()["my_role"] == "leader"


def test_a_team_the_user_cannot_see_answers_404(scenario: TeamScenario) -> None:
    response = client_for(scenario.outsider).get(f"/api/v1/teams/{scenario.team.pk}")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_a_deleted_team_answers_404_even_to_its_members(scenario: TeamScenario) -> None:
    services.delete_team(actor=scenario.admin, team=scenario.team)

    response = client_for(scenario.leader).get(f"/api/v1/teams/{scenario.team.pk}")

    assert response.status_code == 404


def test_every_member_sees_the_member_list_with_roles(scenario: TeamScenario) -> None:
    response = client_for(scenario.member).get(members_url(scenario))

    assert [(m["email"], m["role"]) for m in response.json()] == [
        ("leader@example.com", "leader"),
        ("member@example.com", "member"),
    ]


def test_outsiders_cannot_see_the_member_list(scenario: TeamScenario) -> None:
    assert client_for(scenario.outsider).get(members_url(scenario)).status_code == 404


def test_a_leader_adds_a_member(scenario: TeamScenario) -> None:
    create_user("new@example.com")

    response = client_for(scenario.leader).post(
        members_url(scenario), {"email": "new@example.com"}, format="json"
    )

    assert response.status_code == 201
    assert response.json()["role"] == "member"


def test_a_member_adding_someone_gets_403(scenario: TeamScenario) -> None:
    create_user("new@example.com")

    response = client_for(scenario.member).post(
        members_url(scenario), {"email": "new@example.com"}, format="json"
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_an_invalid_email_is_rejected_with_field_details(scenario: TeamScenario) -> None:
    response = client_for(scenario.leader).post(
        members_url(scenario), {"email": "not-an-email"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid"
    assert "email" in response.json()["details"]


def test_adding_an_existing_member_answers_409(scenario: TeamScenario) -> None:
    response = client_for(scenario.leader).post(
        members_url(scenario), {"email": scenario.member.email}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["code"] == "already_member"


def test_a_leader_promotes_a_member(scenario: TeamScenario) -> None:
    response = client_for(scenario.leader).patch(
        members_url(scenario, scenario.member), {"role": "leader"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["role"] == "leader"


@pytest.mark.parametrize(("role", "status"), [("leader", 403), ("owner", 400)])
def test_role_changes_by_members_or_to_unknown_roles_fail(
    scenario: TeamScenario, role: str, status: int
) -> None:
    client = client_for(scenario.member if status == 403 else scenario.leader)

    response = client.patch(members_url(scenario, scenario.member), {"role": role}, format="json")

    assert response.status_code == status


def test_a_leader_removes_a_member(scenario: TeamScenario) -> None:
    response = client_for(scenario.leader).delete(members_url(scenario, scenario.member))

    assert response.status_code == 204
    assert not Membership.objects.filter(team=scenario.team, user=scenario.member).exists()


def test_a_member_leaves_the_team(scenario: TeamScenario) -> None:
    response = client_for(scenario.member).delete(members_url(scenario, scenario.member))

    assert response.status_code == 204


def test_a_member_removing_the_leader_gets_403(scenario: TeamScenario) -> None:
    response = client_for(scenario.member).delete(members_url(scenario, scenario.leader))

    assert response.status_code == 403


def test_removing_someone_who_is_not_a_member_answers_404(scenario: TeamScenario) -> None:
    response = client_for(scenario.leader).delete(members_url(scenario, scenario.outsider))

    assert response.status_code == 404


def count_queries(action: Callable[[], object]) -> int:
    with CaptureQueriesContext(connection) as queries:
        action()
    return len(queries)


@pytest.mark.django_db
def test_team_list_queries_do_not_grow_with_the_number_of_teams() -> None:
    user = create_user("busy@example.com")
    add_membership(create_team("T0"), user, Role.LEADER)
    client = client_for(user)
    few = count_queries(lambda: client.get("/api/v1/teams"))
    for index in range(1, 6):
        add_membership(create_team(f"T{index}"), user)

    many = count_queries(lambda: client.get("/api/v1/teams"))

    assert many == few == 1


def test_member_list_queries_do_not_grow_with_the_number_of_members(
    scenario: TeamScenario,
) -> None:
    client = client_for(scenario.member)
    few = count_queries(lambda: client.get(members_url(scenario)))
    for index in range(5):
        add_membership(scenario.team, create_user(f"m{index}@example.com"))

    many = count_queries(lambda: client.get(members_url(scenario)))

    assert many == few
