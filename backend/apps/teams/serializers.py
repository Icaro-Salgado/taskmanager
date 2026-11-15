from rest_framework import serializers

from apps.teams.models import Membership, Role, Team


class TeamSerializer(serializers.ModelSerializer[Team]):
    my_role = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Team
        fields = ("id", "name", "archive_after_days", "my_role")
        read_only_fields = fields


class MemberSerializer(serializers.ModelSerializer[Membership]):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    joined_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Membership
        fields = ("user_id", "email", "role", "joined_at")
        read_only_fields = fields


class AddMemberSerializer(serializers.Serializer[None]):
    email = serializers.EmailField()


class ChangeRoleSerializer(serializers.Serializer[None]):
    role = serializers.ChoiceField(choices=Role.choices)
