from django.urls import path

from apps.notifications.views import MarkReadView, NotificationListView

urlpatterns = [
    path("notifications", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<int:notification_id>/read",
        MarkReadView.as_view(),
        name="notification-read",
    ),
]
