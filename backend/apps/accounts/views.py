from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import services
from apps.accounts.auth import authenticated_user
from apps.accounts.serializers import ChangePasswordSerializer, CurrentUserSerializer


class CurrentUserView(APIView):
    def get(self, request: Request) -> Response:
        return Response(CurrentUserSerializer(authenticated_user(request)).data)


class ChangePasswordView(APIView):
    """Changes the password, revokes older tokens and answers a fresh pair for this session."""

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
