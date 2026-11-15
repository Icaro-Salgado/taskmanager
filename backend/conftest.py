from collections.abc import Iterator

import pytest
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from apps.teams.tests.factories import TeamScenario, build_team_scenario
from config.celery import app as celery_app


@pytest.fixture(autouse=True)
def fast_password_hashing(settings: Settings) -> None:
    """Real hashers are slow on purpose; tests only need passwords to round-trip."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def no_throttling(settings: Settings) -> None:
    """Throttling off: a dummy cache never remembers a request. Rate limit tests opt back in."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}


@pytest.fixture(autouse=True)
def celery_eager() -> Iterator[None]:
    """Celery tasks run in-process, so no test needs a broker; their errors reach the test."""
    conf = celery_app.conf
    previous = (conf.task_always_eager, conf.task_eager_propagates)
    conf.task_always_eager = conf.task_eager_propagates = True
    yield
    conf.task_always_eager, conf.task_eager_propagates = previous


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def scenario(db: None) -> TeamScenario:
    """One team with a leader and a member, plus an outsider and a global admin."""
    return build_team_scenario()
