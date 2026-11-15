"""Read queries for notifications. A user only ever sees their own."""

from django.db.models import QuerySet

from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.notifications.models import Notification


def notifications_of(user: User, *, unread_only: bool = False) -> QuerySet[Notification]:
    """Newest first; `id` breaks ties between notifications created in the same instant."""
    notifications = Notification.objects.filter(user=user)
    if unread_only:
        notifications = notifications.filter(read_at__isnull=True)
    return notifications.order_by("-created_at", "-id")


def get_notification_of(user: User, notification_id: int) -> Notification:
    """Someone else's notification is reported as missing, so its existence is not revealed."""
    try:
        return notifications_of(user).get(pk=notification_id)
    except Notification.DoesNotExist as exc:
        raise NotFoundError("Notification not found.") from exc
