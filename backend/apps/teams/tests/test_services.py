import pytest

from apps.accounts.tests.factories import create_user
from apps.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from apps.teams import services
from apps.teams.models import Membership, Role, Team
from apps.teams.tests.factories import TeamScenario


def test_a_leader_adds_a_member_by_email_with_the_member_role(scenario: TeamScenario) -> None:
    newcomer = create_user("new@example.com")

    membership = services.add_member(
        actor=scenario.leader, team=scenario.team, email="New@Example.com"
    )

    assert (membership.user, membership.role) == (newcomer, Role.MEMBER)


def test_an_admin_adds_members_without_being_in_the_team(scenario: TeamScenario) -> None:
    create_user("new@example.com")

    services.add_member(actor=scenario.admin, team=scenario.team, email="new@example.com")


def test_a_member_cannot_add_members(scenario: TeamScenario) -> None:
    create_user("new@example.com")

    with pytest.raises(PermissionDeniedError):
        services.add_member(actor=scenario.member, team=scenario.team, email="new@example.com")


@pytest.mark.parametrize("email", ["nobody@example.com", "inactive@example.com"])
def test_only_existing_active_users_can_be_added(scenario: TeamScenario, email: str) -> None:
    create_user("inactive@example.com", is_active=False)

    with pytest.raises(NotFoundError) as error:
        services.add_member(actor=scenario.leader, team=scenario.team, email=email)

    assert error.value.code == "user_not_found"


def test_adding_an_existing_member_is_a_conflict(scenario: TeamScenario) -> None:
    with pytest.raises(ConflictError):
        services.add_member(actor=scenario.leader, team=scenario.team, email=scenario.member.email)


def test_a_leader_promotes_and_demotes_members_including_themselves(
    scenario: TeamScenario,
) -> None:
    member = Membership.objects.get(team=scenario.team, user=scenario.member)
    own = Membership.objects.get(team=scenario.team, user=scenario.leader)

    services.change_role(actor=scenario.leader, membership=member, role=Role.LEADER)
    services.change_role(actor=scenario.leader, membership=own, role=Role.MEMBER)

    member.refresh_from_db()
    own.refresh_from_db()
    assert (member.role, own.role) == (Role.LEADER, Role.MEMBER)


def test_a_member_cannot_change_roles(scenario: TeamScenario) -> None:
    own = Membership.objects.get(team=scenario.team, user=scenario.member)

    with pytest.raises(PermissionDeniedError):
        services.change_role(actor=scenario.member, membership=own, role=Role.LEADER)


def test_a_leader_removes_another_leader(scenario: TeamScenario) -> None:
    other = create_user("other-leader@example.com")
    membership = Membership.objects.create(team=scenario.team, user=other, role=Role.LEADER)

    services.remove_member(actor=scenario.leader, membership=membership)

    assert not Membership.objects.filter(pk=membership.pk).exists()


def test_any_member_can_leave(scenario: TeamScenario) -> None:
    own = Membership.objects.get(team=scenario.team, user=scenario.member)

    services.remove_member(actor=scenario.member, membership=own)

    assert not Membership.objects.filter(pk=own.pk).exists()


def test_the_last_leader_can_leave_and_the_team_becomes_orphan(scenario: TeamScenario) -> None:
    own = Membership.objects.get(team=scenario.team, user=scenario.leader)

    services.remove_member(actor=scenario.leader, membership=own)

    assert not scenario.team.memberships.filter(role=Role.LEADER).exists()


def test_a_member_cannot_remove_someone_else(scenario: TeamScenario) -> None:
    leader = Membership.objects.get(team=scenario.team, user=scenario.leader)

    with pytest.raises(PermissionDeniedError):
        services.remove_member(actor=scenario.member, membership=leader)


def test_an_admin_soft_deletes_a_team_and_keeps_its_memberships(scenario: TeamScenario) -> None:
    services.delete_team(actor=scenario.admin, team=scenario.team)

    team = Team.objects.get(pk=scenario.team.pk)
    assert team.deleted_at is not None
    assert team.deleted_by == scenario.admin
    assert team.memberships.count() == 2


def test_a_leader_cannot_delete_a_team(scenario: TeamScenario) -> None:
    with pytest.raises(PermissionDeniedError):
        services.delete_team(actor=scenario.leader, team=scenario.team)


def test_a_deleted_team_cannot_be_changed(scenario: TeamScenario) -> None:
    services.delete_team(actor=scenario.admin, team=scenario.team)
    create_user("new@example.com")

    with pytest.raises(NotFoundError):
        services.add_member(actor=scenario.admin, team=scenario.team, email="new@example.com")
    with pytest.raises(NotFoundError):
        services.delete_team(actor=scenario.admin, team=scenario.team)
