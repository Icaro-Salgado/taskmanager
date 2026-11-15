from rest_framework import serializers

from apps.accounts.models import User
from apps.tasks.models import Status, Task


class UserRefSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("id", "email")
        read_only_fields = fields


class TaskSerializer(serializers.ModelSerializer[Task]):
    team = serializers.IntegerField(source="team_id", read_only=True)
    assignee = UserRefSerializer(read_only=True, allow_null=True)
    created_by = UserRefSerializer(read_only=True)
    # Computed by the selectors (due before today in TIME_ZONE and not finished).
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "team",
            "title",
            "description",
            "status",
            "assignee",
            "created_by",
            "due_date",
            "completed_at",
            "is_overdue",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TaskCreateSerializer(serializers.Serializer[None]):
    team = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=Status.choices, default=Status.TODO)
    assignee = serializers.IntegerField(required=False, allow_null=True, default=None)
    due_date = serializers.DateField(required=False, allow_null=True, default=None)


class TaskUpdateSerializer(serializers.Serializer[None]):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Status.choices, required=False)
    assignee = serializers.IntegerField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if "team" in self.initial_data:
            raise serializers.ValidationError({"team": "The team of a task cannot change."})
        return attrs


class TaskFilterSerializer(serializers.Serializer[None]):
    """Query parameters of the task list."""

    team = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=Status.choices, required=False)
    due_after = serializers.DateField(required=False)
    due_before = serializers.DateField(required=False)
    assignee = serializers.CharField(
        required=False, help_text="A user id, or `none` for unassigned tasks."
    )
    overdue = serializers.BooleanField(required=False, allow_null=True, default=None)
    archived = serializers.BooleanField(required=False, default=False)

    def validate_assignee(self, value: str) -> str:
        if value != "none" and not value.isdigit():
            raise serializers.ValidationError("Use a user id or `none`.")
        return value
