import pytest
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def fast_password_hashing(settings: Settings) -> None:
    """Real hashers are slow on purpose; tests only need passwords to round-trip."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()
