"""Read queries for teams. Deleted teams are excluded here explicitly, not by a default manager."""

from django.db.models import OuterRef, QuerySet, Subquery

from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.teams.models import Membership, Role, Team


def active_teams() -> QuerySet[Team]:
    return Team.objects.filter(deleted_at__isnull=True)


def teams_visible_to(user: User) -> QuerySet[Team]:
    """Admins see every active team; everyone else sees the teams they belong to.

    Each team is annotated with `my_role`: the user's role in it, or None for an admin who is not
    a member.
    """
    teams = active_teams()
    if not user.is_superuser:
        teams = teams.filter(memberships__user=user)
    my_role = Membership.objects.filter(team=OuterRef("pk"), user=user).values("role")[:1]
    return teams.annotate(my_role=Subquery(my_role)).order_by("name", "id")


def get_visible_team(user: User, team_id: int) -> Team:
    """The team, or NotFoundError when it does not exist, is deleted or the user cannot see it."""
    try:
        return teams_visible_to(user).get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise NotFoundError("Team not found.") from exc


def role_in(team: Team, user: User) -> Role | None:
    role = Membership.objects.filter(team=team, user=user).values_list("role", flat=True).first()
    return Role(role) if role else None


def members_of(team: Team) -> QuerySet[Membership]:
    return team.memberships.select_related("user").order_by("user__email")


def get_membership(team: Team, user_id: int) -> Membership:
    try:
        return members_of(team).get(user_id=user_id)
    except Membership.DoesNotExist as exc:
        raise NotFoundError("Member not found.") from exc
