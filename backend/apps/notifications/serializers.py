from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer[Notification]):
    team = serializers.IntegerField(source="team_id", read_only=True)
    task = serializers.IntegerField(source="task_id", read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = ("id", "team", "task", "message", "created_at", "read_at")
        read_only_fields = fields


class NotificationPageSerializer(serializers.Serializer[None]):
    """One page of the list, as `NotificationPagination` writes it (documentation only)."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = NotificationSerializer(many=True)


class NotificationFilterSerializer(serializers.Serializer[None]):
    """Query parameters of the list."""

    unread = serializers.BooleanField(
        required=False, default=False, help_text="`true` returns only unread notifications."
    )
