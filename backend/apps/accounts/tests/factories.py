from rest_framework.test import APIClient

from apps.accounts.models import User

TEST_PASSWORD = "correct-Horse-battery-9"  # test-only credential


def create_user(email: str, *, is_superuser: bool = False, is_active: bool = True) -> User:
    # A global admin also gets is_staff, as createsuperuser does, so they can use the admin site.
    user = User.objects.create_user(
        email, TEST_PASSWORD, is_superuser=is_superuser, is_staff=is_superuser
    )
    if not is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
    return user


def client_for(user: User) -> APIClient:
    """An API client authenticated as `user`, skipping the token round trip."""
    client = APIClient()
    client.force_authenticate(user)
    return client
