from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.models import User
from apps.core.exceptions import RuleViolationError


def change_password(*, user: User, current_password: str, new_password: str) -> None:
    """Change the password and revoke every refresh token issued before the change.

    Access tokens issued before are rejected too: they carry a hash of the old password
    (SimpleJWT `CHECK_REVOKE_TOKEN`).
    """
    if not user.check_password(current_password):
        raise RuleViolationError("The current password is wrong.", code="wrong_password")
    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        raise RuleViolationError(" ".join(exc.messages), code="weak_password") from exc

    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        _revoke_refresh_tokens(user)


def _revoke_refresh_tokens(user: User) -> None:
    outstanding = OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding], ignore_conflicts=True
    )
