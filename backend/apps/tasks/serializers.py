from rest_framework import serializers

from apps.accounts.models import User
from apps.tasks import policies
from apps.tasks.models import Status, Task
from apps.teams.models import Role


def _viewer_role(task: Task) -> Role | None:
    # Annotated by selectors.tasks_visible_to; read without a default so a task fetched any
    # other way fails loudly instead of being judged as if the viewer were not a member.
    role: str | None = getattr(task, "viewer_role")  # noqa: B009 - an annotation, unknown to mypy
    return Role(role) if role else None


class UserRefSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("id", "email")
        read_only_fields = fields


class TaskSerializer(serializers.ModelSerializer[Task]):
    """A task as the user in `context["viewer"]` sees it.

    Expects a task from `selectors.tasks_visible_to`, which annotates `is_overdue` and
    `viewer_role`.
    """

    team = serializers.IntegerField(source="team_id", read_only=True)
    assignee = UserRefSerializer(read_only=True, allow_null=True)
    created_by = UserRefSerializer(read_only=True)
    # Computed by the selectors (due before today in TIME_ZONE and not finished).
    is_overdue = serializers.BooleanField(read_only=True)
    # What the viewer may do, from the task policies, so the frontend never decides it.
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    def get_can_edit(self, task: Task) -> bool:
        return policies.can_edit_task_with_role(self._viewer(), task, _viewer_role(task))

    def get_can_delete(self, task: Task) -> bool:
        return policies.can_delete_task_with_role(self._viewer(), task, _viewer_role(task))

    def _viewer(self) -> User:
        viewer = self.context["viewer"]
        assert isinstance(viewer, User)  # noqa: S101 - narrows the type for mypy; cannot fail
        return viewer

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
            "can_edit",
            "can_delete",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TaskPageSerializer(serializers.Serializer[None]):
    """One page of the task list, as `TaskPagination` writes it (documentation only)."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = TaskSerializer(many=True)


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
