import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_an_unknown_api_path_answers_the_json_error_shape(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not found.", "details": None}


def test_other_unknown_paths_keep_the_html_page(api_client: APIClient) -> None:
    response = api_client.get("/does-not-exist")

    assert response.status_code == 404
    assert response["Content-Type"].startswith("text/html")
