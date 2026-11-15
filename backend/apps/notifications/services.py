"""The only write path for notifications. This app stores and delivers; it knows no task rule."""

from django.utils import timezone

from apps.accounts.models import User
from apps.notifications import selectors
from apps.notifications.models import Notification
from apps.teams.models import Team


def create_notification(
    *, user: User, team: Team, message: str, task_id: int | None = None
) -> Notification | None:
    """Creates the notification, or nothing for a deactivated user (they receive none)."""
    if not user.is_active:
        return None
    return Notification.objects.create(user=user, team=team, task_id=task_id, message=message)


def mark_read(*, user: User, notification_id: int) -> Notification:
    """Idempotent: reading it again keeps the first read time. Only the owner may (else 404)."""
    notification = selectors.get_notification_of(user, notification_id)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
    return notification
