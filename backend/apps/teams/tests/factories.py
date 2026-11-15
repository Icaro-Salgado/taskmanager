from dataclasses import dataclass

from apps.accounts.models import User
from apps.accounts.tests.factories import create_user
from apps.teams.models import Membership, Role, Team


def create_team(name: str = "Alpha", *, archive_after_days: int = 15) -> Team:
    return Team.objects.create(name=name, archive_after_days=archive_after_days)


def add_membership(team: Team, user: User, role: Role = Role.MEMBER) -> Membership:
    return Membership.objects.create(team=team, user=user, role=role)


@dataclass(frozen=True)
class TeamScenario:
    """One team with a leader and a member, plus an outsider and a global admin."""

    team: Team
    leader: User
    member: User
    outsider: User
    admin: User


def build_team_scenario() -> TeamScenario:
    team = create_team()
    leader = create_user("leader@example.com")
    member = create_user("member@example.com")
    add_membership(team, leader, Role.LEADER)
    add_membership(team, member)
    return TeamScenario(
        team=team,
        leader=leader,
        member=member,
        outsider=create_user("outsider@example.com"),
        admin=create_user("admin@example.com", is_superuser=True),
    )
