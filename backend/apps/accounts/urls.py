from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.accounts.views import ChangePasswordView, CurrentUserView

urlpatterns = [
    path("auth/token", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout", TokenBlacklistView.as_view(), name="logout"),
    path("auth/me", CurrentUserView.as_view(), name="current-user"),
    path("auth/password", ChangePasswordView.as_view(), name="change-password"),
]
