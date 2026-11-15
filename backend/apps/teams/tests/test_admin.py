import pytest
from django.test import Client

from apps.accounts.models import User
from apps.accounts.tests.factories import create_user
from apps.teams.models import Membership, Role, Team
from apps.teams.tests.factories import TeamScenario, add_membership, create_team


@pytest.fixture
def admin_site(scenario: TeamScenario) -> Client:
    client = Client()
    client.force_login(scenario.admin)
    return client


@pytest.mark.parametrize(
    "path", ["/admin/teams/team/", "/admin/teams/membership/", "/admin/accounts/user/"]
)
def test_superusers_manage_everything(admin_site: Client, path: str) -> None:
    assert admin_site.get(path).status_code == 200


@pytest.mark.django_db
def test_staff_who_are_not_admins_can_log_in_but_manage_nothing() -> None:
    staff = create_user("staff@example.com")
    User.objects.filter(pk=staff.pk).update(is_staff=True)
    client = Client()
    client.force_login(User.objects.get(pk=staff.pk))

    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/teams/team/").status_code == 403


def test_the_bulk_delete_action_is_not_offered(admin_site: Client) -> None:
    response = admin_site.get("/admin/teams/team/")

    assert b"delete_selected" not in response.content


def test_the_orphan_filter_lists_teams_without_a_leader(
    admin_site: Client, scenario: TeamScenario
) -> None:
    add_membership(create_team("Orphan"), scenario.member)

    response = admin_site.get("/admin/teams/team/", {"leaders": "none"})

    teams = [str(team) for team in response.context["cl"].result_list]
    assert teams == ["Orphan"]


def test_deleting_a_team_in_the_admin_is_a_soft_delete(
    admin_site: Client, scenario: TeamScenario
) -> None:
    url = f"/admin/teams/team/{scenario.team.pk}/delete/"

    confirmation = admin_site.get(url)
    admin_site.post(url, {"post": "yes"})

    assert confirmation.context["deleted_objects"] == ["Alpha"]  # memberships are not deleted
    team = Team.objects.get(pk=scenario.team.pk)
    assert team.deleted_by == scenario.admin
    assert team.memberships.count() == 2


@pytest.mark.parametrize("role", [Role.LEADER, Role.MEMBER])
def test_adding_a_membership_in_the_admin_goes_through_the_services(
    admin_site: Client, scenario: TeamScenario, role: Role
) -> None:
    newcomer = create_user("new@example.com")

    admin_site.post(
        "/admin/teams/membership/add/",
        {"team": scenario.team.pk, "user": newcomer.pk, "role": role.value},
    )

    assert Membership.objects.get(team=scenario.team, user=newcomer).role == role


def test_inactive_users_cannot_be_picked_in_the_admin(
    admin_site: Client, scenario: TeamScenario
) -> None:
    inactive = create_user("gone@example.com", is_active=False)

    response = admin_site.post(
        "/admin/teams/membership/add/",
        {"team": scenario.team.pk, "user": inactive.pk, "role": "member"},
    )

    assert response.status_code == 200  # the form comes back with an error
    assert not Membership.objects.filter(user=inactive).exists()


def test_changing_and_removing_a_membership_in_the_admin(
    admin_site: Client, scenario: TeamScenario
) -> None:
    membership = Membership.objects.get(team=scenario.team, user=scenario.member)
    url = f"/admin/teams/membership/{membership.pk}/"

    admin_site.post(f"{url}change/", {"role": "leader"})
    membership.refresh_from_db()
    promoted = membership.role
    admin_site.post(f"{url}delete/", {"post": "yes"})

    assert promoted == Role.LEADER
    assert not Membership.objects.filter(pk=membership.pk).exists()


def test_users_cannot_be_deleted_in_the_admin(admin_site: Client, scenario: TeamScenario) -> None:
    response = admin_site.get(f"/admin/accounts/user/{scenario.member.pk}/delete/")

    assert response.status_code == 403


def test_users_created_in_the_admin_get_a_lowercase_email(admin_site: Client) -> None:
    admin_site.post(
        "/admin/accounts/user/add/",
        {
            "email": "New.Person@Example.com",
            "password1": "",
            "password2": "",
            "usable_password": "false",
        },
    )

    assert User.objects.filter(email="new.person@example.com").exists()
