import pytest
from django.http import Http404
from rest_framework.exceptions import ValidationError

from apps.core.exception_handler import handle_exception
from apps.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
)


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (NotFoundError("Team not found."), 404, "not_found"),
        (PermissionDeniedError("No."), 403, "permission_denied"),
        (RuleViolationError("Finished tasks are read-only."), 400, "rule_violation"),
        (ConflictError("Already a member.", code="already_member"), 409, "already_member"),
        (DomainError("Something else."), 400, "domain_error"),
    ],
)
def test_domain_errors_map_to_http_with_the_common_shape(
    error: DomainError, status: int, code: str
) -> None:
    response = handle_exception(error, {})

    assert response is not None
    assert response.status_code == status
    assert response.data == {"code": code, "message": error.message, "details": None}


def test_validation_errors_keep_the_field_details() -> None:
    response = handle_exception(ValidationError({"email": ["Enter a valid email address."]}), {})

    assert response is not None
    assert response.status_code == 400
    assert response.data["code"] == "invalid"
    assert response.data["details"] == {"email": ["Enter a valid email address."]}


def test_django_404_gets_the_common_shape() -> None:
    response = handle_exception(Http404(), {})

    assert response is not None
    assert response.status_code == 404
    assert response.data["code"] == "not_found"


def test_unexpected_errors_are_left_to_django() -> None:
    assert handle_exception(RuntimeError("boom"), {}) is None
