from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimestampedModel


def normalize_email(email: str) -> str:
    """Emails are the login and are stored lowercase, so lookups are case-insensitive."""
    return email.strip().lower()


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def get_by_natural_key(self, username: str | None) -> "User":
        # Used by the login backend: "Alice@Example.com" finds "alice@example.com".
        return self.get(email=normalize_email(username or ""))

    def create_user(
        self,
        email: str,
        password: str | None = None,
        *,
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> "User":
        user = self.model(
            email=normalize_email(email), is_staff=is_staff, is_superuser=is_superuser
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None) -> "User":
        return self.create_user(email, password, is_staff=True, is_superuser=True)


class User(TimestampedModel, AbstractBaseUser, PermissionsMixin):
    """Login by email. Never deleted: deactivate with `is_active = False`.

    `is_superuser` is the global admin; `is_staff` only allows logging in to the Django admin site.
    """

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=Lower("email")), name="accounts_user_email_lowercase"
            ),
        ]

    def __str__(self) -> str:
        return self.email

    def clean(self) -> None:
        super().clean()
        self.email = normalize_email(self.email)
