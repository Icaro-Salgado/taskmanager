from pathlib import Path

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient


def test_the_schema_generates_without_warnings(tmp_path: Path) -> None:
    """Every endpoint documents its request and responses; a guess would be a warning."""
    target = tmp_path / "schema.yml"

    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(target))

    assert "/api/v1/tasks/{task_id}/reopen" in target.read_text()


@pytest.mark.django_db
def test_the_schema_and_swagger_ui_are_served(api_client: APIClient) -> None:
    schema = api_client.get("/api/v1/schema")
    docs = api_client.get("/api/v1/docs")

    assert schema.status_code == 200
    assert b"openapi: 3" in schema.content
    assert docs.status_code == 200
    assert b"swagger-ui" in docs.content
