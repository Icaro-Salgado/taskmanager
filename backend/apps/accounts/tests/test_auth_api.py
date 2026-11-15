import jwt
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import TEST_PASSWORD, create_user

pytestmark = pytest.mark.django_db

TOKEN_URL = "/api/v1/auth/token"
REFRESH_URL = "/api/v1/auth/token/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"
PASSWORD_URL = "/api/v1/auth/password"
NEW_PASSWORD = "another-Strong-pass-42"


def login(client: APIClient, email: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    response = client.post(TOKEN_URL, {"email": email, "password": password}, format="json")
    assert response.status_code == 200, response.json()
    tokens: dict[str, str] = response.json()
    return tokens


def bearer(access: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def test_login_returns_an_access_and_a_refresh_token(api_client: APIClient) -> None:
    create_user("alice@example.com")

    tokens = login(api_client, "alice@example.com")

    assert set(tokens) == {"access", "refresh"}


def test_access_tokens_last_15_minutes(api_client: APIClient) -> None:
    create_user("alice@example.com")

    access = login(api_client, "alice@example.com")["access"]
    claims = jwt.decode(access, options={"verify_signature": False})

    assert claims["exp"] - claims["iat"] == 15 * 60


def test_login_email_is_case_insensitive(api_client: APIClient) -> None:
    create_user("alice@example.com")

    login(api_client, "Alice@EXAMPLE.com")


def test_wrong_password_is_rejected_with_the_common_error_shape(api_client: APIClient) -> None:
    create_user("alice@example.com")

    response = api_client.post(
        TOKEN_URL, {"email": "alice@example.com", "password": "wrong"}, format="json"
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "no_active_account",
        "message": "No active account found with the given credentials",
        "details": None,
    }


def test_a_deactivated_user_cannot_log_in(api_client: APIClient) -> None:
    create_user("alice@example.com", is_active=False)

    response = api_client.post(
        TOKEN_URL, {"email": "alice@example.com", "password": TEST_PASSWORD}, format="json"
    )

    assert response.status_code == 401


def test_a_user_deactivated_after_login_is_rejected(api_client: APIClient) -> None:
    user = create_user("alice@example.com")
    access = login(api_client, user.email)["access"]
    User.objects.filter(pk=user.pk).update(is_active=False)

    response = bearer(access).get(ME_URL)

    assert response.status_code == 401
    assert response.json()["code"] == "user_inactive"


def test_refresh_rotates_and_the_used_refresh_token_is_blacklisted(api_client: APIClient) -> None:
    create_user("alice@example.com")
    first = login(api_client, "alice@example.com")["refresh"]

    response = api_client.post(REFRESH_URL, {"refresh": first}, format="json")
    reused = api_client.post(REFRESH_URL, {"refresh": first}, format="json")

    assert response.status_code == 200
    assert response.json()["refresh"] != first
    assert reused.status_code == 401
    assert reused.json()["code"] == "token_not_valid"


def test_logout_blacklists_the_refresh_token(api_client: APIClient) -> None:
    create_user("alice@example.com")
    refresh = login(api_client, "alice@example.com")["refresh"]

    logout = api_client.post(LOGOUT_URL, {"refresh": refresh}, format="json")
    after = api_client.post(REFRESH_URL, {"refresh": refresh}, format="json")

    assert logout.status_code == 200
    assert after.status_code == 401


def test_current_user_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_current_user_returns_the_profile_and_the_admin_flag(api_client: APIClient) -> None:
    admin = create_user("root@example.com", is_superuser=True)
    access = login(api_client, admin.email)["access"]

    response = bearer(access).get(ME_URL)

    assert response.json() == {"id": admin.pk, "email": "root@example.com", "is_admin": True}


def change_password(access: str, current: str, new: str) -> tuple[int, dict[str, object]]:
    response = bearer(access).post(
        PASSWORD_URL, {"current_password": current, "new_password": new}, format="json"
    )
    body: dict[str, object] = response.json()
    return response.status_code, body


def test_change_password_requires_the_current_password(api_client: APIClient) -> None:
    create_user("alice@example.com")
    access = login(api_client, "alice@example.com")["access"]

    status, body = change_password(access, "wrong", NEW_PASSWORD)

    assert status == 400
    assert body["code"] == "wrong_password"


def test_change_password_runs_the_password_validators(api_client: APIClient) -> None:
    create_user("alice@example.com")
    access = login(api_client, "alice@example.com")["access"]

    status, body = change_password(access, TEST_PASSWORD, "12345678")

    assert status == 400
    assert body["code"] == "weak_password"


def test_change_password_revokes_older_tokens_and_returns_a_fresh_pair(
    api_client: APIClient,
) -> None:
    create_user("alice@example.com")
    old = login(api_client, "alice@example.com")

    status, fresh = change_password(old["access"], TEST_PASSWORD, NEW_PASSWORD)

    assert status == 200
    old_access = bearer(old["access"]).get(ME_URL)
    assert old_access.status_code == 401
    assert old_access.json()["code"] == "password_changed"
    old_refresh = api_client.post(REFRESH_URL, {"refresh": old["refresh"]}, format="json")
    assert old_refresh.status_code == 401
    assert bearer(str(fresh["access"])).get(ME_URL).status_code == 200
    login(api_client, "alice@example.com", NEW_PASSWORD)
