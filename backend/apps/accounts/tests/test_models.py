import pytest
from django.db import IntegrityError

from apps.accounts.models import User
from apps.accounts.tests.factories import TEST_PASSWORD

pytestmark = pytest.mark.django_db


def test_create_user_stores_the_email_lowercase_and_trimmed() -> None:
    user = User.objects.create_user("  Alice@Example.COM ", TEST_PASSWORD)

    assert user.email == "alice@example.com"
    assert user.check_password(TEST_PASSWORD)
    assert (user.is_active, user.is_staff, user.is_superuser) == (True, False, False)
    assert str(user) == "alice@example.com"


def test_create_superuser_is_a_global_admin_who_can_use_the_admin_site() -> None:
    user = User.objects.create_superuser("root@example.com", TEST_PASSWORD)

    assert (user.is_superuser, user.is_staff) == (True, True)


def test_login_lookup_ignores_case() -> None:
    user = User.objects.create_user("alice@example.com", TEST_PASSWORD)

    assert User.objects.get_by_natural_key("ALICE@example.com") == user


def test_the_database_rejects_an_email_that_is_not_lowercase() -> None:
    with pytest.raises(IntegrityError):
        User.objects.create(email="Bob@example.com")


def test_clean_lowercases_the_email() -> None:
    user = User(email="Carol@Example.com")

    user.clean()

    assert user.email == "carol@example.com"
