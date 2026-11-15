"""OpenAPI helpers shared by the API views (documentation only; no behaviour)."""

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers

_DESCRIPTIONS = {
    400: "Invalid input or a broken rule (`code` says which).",
    401: "Missing, expired or revoked token.",
    403: "The resource is visible but the action is not allowed.",
    404: "Not found, or in a team the caller cannot see.",
    409: "Conflicts with the current state.",
    429: "Rate limit reached; see the `Retry-After` header.",
}


class ErrorSerializer(serializers.Serializer[None]):
    """The single error shape, produced by `apps.core.exception_handler`."""

    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField(allow_null=True)


def errors(*statuses: int, public: bool = False) -> dict[int, OpenApiResponse]:
    """Error responses of an endpoint. 429 always applies; 401 unless the endpoint is public."""
    codes = sorted({*statuses, 429} if public else {*statuses, 401, 429})
    return {
        code: OpenApiResponse(ErrorSerializer, description=_DESCRIPTIONS[code]) for code in codes
    }
