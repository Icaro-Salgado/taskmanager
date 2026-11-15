from rest_framework import serializers

from apps.accounts.models import User


class CurrentUserSerializer(serializers.ModelSerializer[User]):
    is_admin = serializers.BooleanField(source="is_superuser", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "is_admin")
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer[None]):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
