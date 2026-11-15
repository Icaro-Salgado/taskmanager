from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimestampedModel


class Team(TimestampedModel):
    """Soft-deleted: `deleted_at` is set instead of removing the row (restore with a SQL UPDATE)."""

    name = models.CharField(max_length=30)
    archive_after_days = models.PositiveIntegerField(default=15, validators=[MinValueValidator(1)])
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        constraints = [
            # Unique among teams that are not deleted, ignoring case. Restoring a deleted team fails
            # if an active team has taken its name meanwhile.
            models.UniqueConstraint(
                Lower("name"),
                condition=models.Q(deleted_at__isnull=True),
                name="teams_team_name_unique_active",
                violation_error_message="A team with this name already exists.",
            ),
            models.CheckConstraint(
                condition=models.Q(archive_after_days__gte=1),
                name="teams_team_archive_after_days_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Role(models.TextChoices):
    LEADER = "leader", "Leader"
    MEMBER = "member", "Member"


class Membership(TimestampedModel):
    # limit_choices_to only narrows the admin form choices; the services enforce the rules.
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
        limit_choices_to={"deleted_at__isnull": True},
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        limit_choices_to={"is_active": True},
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="teams_membership_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.team} ({self.role})"
