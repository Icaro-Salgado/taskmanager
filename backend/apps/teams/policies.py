"""Who may do what on a team. Pure answers; services raise the errors."""

from apps.accounts.models import User
from apps.teams import selectors
from apps.teams.models import Role, Team


def is_admin(user: User) -> bool:
    return user.is_superuser


def can_manage_members(user: User, team: Team) -> bool:
    """Add members, change roles and remove anyone: team leaders and admins."""
    return is_admin(user) or selectors.role_in(team, user) == Role.LEADER


def can_remove_member(actor: User, team: Team, member: User) -> bool:
    """Leaders and admins remove anyone; every member may leave."""
    return actor.pk == member.pk or can_manage_members(actor, team)


def can_delete_team(user: User) -> bool:
    return is_admin(user)
