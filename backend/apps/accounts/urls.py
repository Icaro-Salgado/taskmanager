from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    CurrentUserView,
    LoginView,
    LogoutView,
    RefreshView,
)

urlpatterns = [
    path("auth/token", LoginView.as_view(), name="token-obtain"),
    path("auth/token/refresh", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("auth/me", CurrentUserView.as_view(), name="current-user"),
    path("auth/password", ChangePasswordView.as_view(), name="change-password"),
]
