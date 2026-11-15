import pytest
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from apps.teams.tests.factories import TeamScenario, build_team_scenario


@pytest.fixture(autouse=True)
def fast_password_hashing(settings: Settings) -> None:
    """Real hashers are slow on purpose; tests only need passwords to round-trip."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def scenario(db: None) -> TeamScenario:
    """One team with a leader and a member, plus an outsider and a global admin."""
    return build_team_scenario()
