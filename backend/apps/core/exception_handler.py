"""The single DRF exception handler: every error leaves the API with the same JSON shape.

{"code": "<machine-readable>", "message": "<human-readable>", "details": <field errors or null>}
"""

from collections.abc import Mapping

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
)

_DOMAIN_STATUS: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    RuleViolationError: status.HTTP_400_BAD_REQUEST,
    ConflictError: status.HTTP_409_CONFLICT,
}


def error_body(code: str, message: str, details: object = None) -> dict[str, object]:
    return {"code": code, "message": message, "details": details}


def _domain_status(exc: DomainError) -> int:
    for exc_class, http_status in _DOMAIN_STATUS.items():
        if isinstance(exc, exc_class):
            return http_status
    return status.HTTP_400_BAD_REQUEST


def _body_from_drf(exc: Exception, data: Mapping[str, object]) -> dict[str, object]:
    if isinstance(exc, ValidationError):
        return error_body("invalid", "Invalid input.", details=data)
    # Every other DRF error carries a {"detail": ...} mapping.
    detail = data.get("detail", "")
    # SimpleJWT puts its own code next to the detail; DRF keeps it on the ErrorDetail.
    code = data.get("code") or getattr(detail, "code", None) or "error"
    return error_body(str(code), str(detail))


def handle_exception(exc: Exception, context: Mapping[str, object]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response(error_body(exc.code, exc.message), status=_domain_status(exc))
    response = drf_exception_handler(exc, dict(context))
    if response is None:
        return None  # Unexpected error: Django answers 500 and logs the traceback.
    response.data = _body_from_drf(exc, response.data)
    return response
