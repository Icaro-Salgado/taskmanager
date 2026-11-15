from collections.abc import Iterator

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient
from rest_framework.throttling import UserRateThrottle

from apps.accounts.tests.factories import TEST_PASSWORD, client_for, create_user

pytestmark = pytest.mark.django_db

TOKEN_URL = "/api/v1/auth/token"


def set_proxies(settings: Settings, count: int) -> None:
    settings.REST_FRAMEWORK = {**django_settings.REST_FRAMEWORK, "NUM_PROXIES": count}


@pytest.fixture(autouse=True)
def throttling(settings: Settings) -> Iterator[None]:
    """Turns throttling back on (conftest turns it off) with a cache local to the test.

    No proxy by default, whatever DRF_NUM_PROXIES says where the tests run (the compose api
    service sets it to 1 for nginx).
    """
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    set_proxies(settings, 0)
    cache.clear()
    yield
    cache.clear()


def attempt(
    client: APIClient,
    password: str = TEST_PASSWORD,
    remote_addr: str = "127.0.0.1",
    forwarded_for: str = "",
) -> int:
    response = client.post(
        TOKEN_URL,
        {"email": "alice@example.com", "password": password},
        format="json",
        REMOTE_ADDR=remote_addr,
        HTTP_X_FORWARDED_FOR=forwarded_for,
    )
    return response.status_code


def test_the_default_limits_are_5_logins_and_300_requests_per_minute() -> None:
    rates = django_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    assert rates == {"login": "5/min", "user": "300/min"}


def test_the_sixth_login_in_a_minute_is_refused(api_client: APIClient) -> None:
    create_user("alice@example.com")

    assert [attempt(api_client) for _ in range(5)] == [200] * 5
    response = api_client.post(
        TOKEN_URL, {"email": "alice@example.com", "password": TEST_PASSWORD}, format="json"
    )

    assert response.status_code == 429
    assert response.json()["code"] == "throttled"
    assert int(response["Retry-After"]) > 0


def test_failed_logins_count_toward_the_limit(api_client: APIClient) -> None:
    create_user("alice@example.com")

    assert [attempt(api_client, password="wrong") for _ in range(5)] == [401] * 5
    assert attempt(api_client) == 429


def test_the_login_limit_is_per_client_address(api_client: APIClient) -> None:
    create_user("alice@example.com")
    for _ in range(5):
        attempt(api_client, remote_addr="10.0.0.1")

    assert attempt(api_client, remote_addr="10.0.0.1") == 429
    assert attempt(api_client, remote_addr="10.0.0.2") == 200


def test_a_forged_forwarded_address_does_not_reset_the_login_limit(api_client: APIClient) -> None:
    """With no proxy configured, X-Forwarded-For comes from the client and is ignored."""
    create_user("alice@example.com")
    for i in range(5):
        attempt(api_client, forwarded_for=f"203.0.113.{i}")

    assert attempt(api_client, forwarded_for="203.0.113.99") == 429


def test_behind_one_proxy_the_limit_is_per_forwarded_address(
    api_client: APIClient, settings: Settings
) -> None:
    """nginx replaces X-Forwarded-For with the client address, so each client has its own count."""
    set_proxies(settings, 1)
    create_user("alice@example.com")
    for _ in range(5):
        attempt(api_client, remote_addr="172.18.0.5", forwarded_for="203.0.113.1")

    assert attempt(api_client, remote_addr="172.18.0.5", forwarded_for="203.0.113.1") == 429
    assert attempt(api_client, remote_addr="172.18.0.5", forwarded_for="203.0.113.2") == 200


def test_the_general_limit_is_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(UserRateThrottle, "rate", "3/min", raising=False)
    alice = client_for(create_user("alice@example.com"))
    bob = client_for(create_user("bob@example.com"))

    assert [alice.get("/api/v1/auth/me").status_code for _ in range(4)] == [200, 200, 200, 429]
    assert bob.get("/api/v1/auth/me").status_code == 200


def test_the_health_check_is_never_throttled(
    api_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(UserRateThrottle, "rate", "1/min", raising=False)

    assert [api_client.get("/api/v1/health").status_code for _ in range(3)] == [200] * 3
