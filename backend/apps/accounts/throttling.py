from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class LoginRateThrottle(SimpleRateThrottle):
    """Counts login attempts per client address, failed or not, whatever the request carries."""

    scope = "login"

    def get_cache_key(self, request: Request, view: APIView) -> str:  # noqa: ARG002 (DRF hook signature)
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
