from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel
from apps.teams.models import Team


class Notification(TimestampedModel):
    """A message for one user. Who is notified about what is decided by the app owning the rule."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="notifications")
    # Declared by name: notifications comes before tasks and never imports it. Null for a message
    # about several tasks of a team.
    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user}: {self.message}"
