"""The only write path for teams and memberships, used by the API views and the admin site."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.selectors import find_active_user_by_email
from apps.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from apps.tasks.services import unassign_member_tasks
from apps.teams import policies
from apps.teams.models import Membership, Role, Team


def _ensure_active(team: Team) -> None:
    if team.deleted_at is not None:
        raise NotFoundError("Team not found.")


def delete_team(*, actor: User, team: Team) -> None:
    """Soft delete: memberships and tasks stay untouched, so a restore brings everything back."""
    _ensure_active(team)
    if not policies.can_delete_team(actor):
        raise PermissionDeniedError("Only admins can delete teams.")
    team.deleted_at = timezone.now()
    team.deleted_by = actor
    team.save(update_fields=["deleted_at", "deleted_by", "updated_at"])


def add_member(*, actor: User, team: Team, email: str) -> Membership:
    """Adds an active user, found by exact email, always with the member role."""
    _ensure_active(team)
    if not policies.can_manage_members(actor, team):
        raise PermissionDeniedError("Only team leaders can add members.")
    user = find_active_user_by_email(email)
    if user is None:
        raise NotFoundError("No active user with this email.", code="user_not_found")
    try:
        with transaction.atomic():
            return Membership.objects.create(team=team, user=user, role=Role.MEMBER)
    except IntegrityError as exc:
        raise ConflictError("This user is already a member.", code="already_member") from exc


def change_role(*, actor: User, membership: Membership, role: Role) -> Membership:
    _ensure_active(membership.team)
    if not policies.can_manage_members(actor, membership.team):
        raise PermissionDeniedError("Only team leaders can change roles.")
    membership.role = role
    membership.save(update_fields=["role", "updated_at"])
    return membership


def remove_member(*, actor: User, membership: Membership) -> None:
    """Removes a member, or lets a member leave. A team may end up with no leader.

    Their tasks in this team are unassigned in the same transaction, so an assignee is always a
    member. The membership row is locked first (see `tasks.services._assignee_for`). This is the
    one call from `teams` into `tasks` (an explicit call, not a signal).
    """
    _ensure_active(membership.team)
    if not policies.can_remove_member(actor, membership.team, membership.user):
        raise PermissionDeniedError("Only team leaders can remove other members.")
    with transaction.atomic():
        # Locked first: an assignment to this member running at the same time either finishes
        # before the unassignment below, or waits and then finds no membership.
        if not list(Membership.objects.select_for_update().filter(pk=membership.pk)):
            raise NotFoundError("Membership not found.")
        unassign_member_tasks(team=membership.team, user=membership.user)
        membership.delete()
