from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.defaults import page_not_found
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exception_handler import error_body


def database_is_reachable() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return False
    return True


class HealthView(APIView):
    """Liveness probe for compose and the proxy: public, and it checks the database."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = ()  # probes run every few seconds and must never be refused

    @extend_schema(
        responses={
            200: inline_serializer("Health", {"status": serializers.CharField()}),
            503: inline_serializer("HealthDown", {"status": serializers.CharField()}),
        },
    )
    def get(self, request: Request) -> Response:
        if database_is_reachable():
            return Response({"status": "ok"})
        return Response({"status": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Django's 404 handler: unknown API paths answer the JSON error shape, the rest HTML."""
    if request.path.startswith("/api/"):
        return JsonResponse(error_body("not_found", "Not found."), status=404)
    return page_not_found(request, exception)
