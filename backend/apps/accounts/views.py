from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.accounts import services
from apps.accounts.auth import authenticated_user
from apps.accounts.serializers import ChangePasswordSerializer, CurrentUserSerializer
from apps.accounts.throttling import LoginRateThrottle
from apps.core.schema import errors

TokenPairSerializer = inline_serializer(
    "TokenPair", {"access": serializers.CharField(), "refresh": serializers.CharField()}
)


@extend_schema_view(
    post=extend_schema(
        responses={200: TokenPairSerializer, **errors(400, 401, public=True)},
        description="Log in with email and password. Limited per client address (5 per minute "
        "by default), failed attempts included.",
    )
)
class LoginView(TokenObtainPairView):
    """SimpleJWT's token endpoint with the strict login rate limit instead of the per-user one."""

    throttle_classes = (LoginRateThrottle,)


@extend_schema_view(
    post=extend_schema(
        responses={200: TokenPairSerializer, **errors(400, 401, public=True)},
        description="Returns a new access and a new refresh token; the refresh token sent is "
        "blacklisted and cannot be used again.",
    )
)
class RefreshView(TokenRefreshView):
    pass


@extend_schema_view(
    post=extend_schema(
        responses={200: None, **errors(400, 401, public=True)},
        description="Blacklists the refresh token sent.",
    )
)
class LogoutView(TokenBlacklistView):
    pass


class CurrentUserView(APIView):
    @extend_schema(responses={200: CurrentUserSerializer, **errors()})
    def get(self, request: Request) -> Response:
        return Response(CurrentUserSerializer(authenticated_user(request)).data)


class ChangePasswordView(APIView):
    """Changes the password, revokes older tokens and answers a fresh pair for this session."""

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: TokenPairSerializer, **errors(400)},
    )
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticated_user(request)
        services.change_password(
            user=user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
        )
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
