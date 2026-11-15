from unittest.mock import patch

import pytest
from django.db import DatabaseError
from rest_framework.test import APIClient

HEALTH_URL = "/api/v1/health"


@pytest.mark.django_db
def test_health_is_public_and_reports_ok() -> None:
    response = APIClient().get(HEALTH_URL)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_unavailable_when_the_database_is_down() -> None:
    with patch("apps.core.views.connection.cursor", side_effect=DatabaseError):
        response = APIClient().get(HEALTH_URL)

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
