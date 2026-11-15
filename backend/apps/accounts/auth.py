from django.http import HttpRequest
from rest_framework.request import Request

from apps.accounts.models import User


def authenticated_user(request: Request | HttpRequest) -> User:
    """The logged-in user, typed for the services.

    Only called behind a login check (DRF's default IsAuthenticated, or the admin site), so the
    user is never anonymous here.
    """
    user = request.user
    assert isinstance(user, User)  # noqa: S101 - narrows the type for mypy; cannot fail
    return user
