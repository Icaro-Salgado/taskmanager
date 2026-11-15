from django.db import DatabaseError, connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


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

    def get(self, request: Request) -> Response:
        if database_is_reachable():
            return Response({"status": "ok"})
        return Response({"status": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
