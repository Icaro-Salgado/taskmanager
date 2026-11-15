from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import authenticated_user
from apps.core.schema import errors
from apps.notifications import selectors, services
from apps.notifications.serializers import (
    NotificationFilterSerializer,
    NotificationPageSerializer,
    NotificationSerializer,
)


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationListView(APIView):
    @extend_schema(
        operation_id="notifications_list",
        parameters=[NotificationFilterSerializer],
        responses={200: NotificationPageSerializer, **errors(400)},
        description="The caller's notifications, newest first. `unread=true` keeps only the "
        "unread ones.",
    )
    def get(self, request: Request) -> Response:
        params = NotificationFilterSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        notifications = selectors.notifications_of(
            authenticated_user(request), unread_only=params.validated_data["unread"]
        )
        paginator = NotificationPagination()
        page = paginator.paginate_queryset(notifications, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class MarkReadView(APIView):
    @extend_schema(
        request=None,
        responses={200: NotificationSerializer, **errors(404)},
        description="Marks one of the caller's notifications as read. Marking it again changes "
        "nothing.",
    )
    def post(self, request: Request, notification_id: int) -> Response:
        notification = services.mark_read(
            user=authenticated_user(request), notification_id=notification_id
        )
        return Response(NotificationSerializer(notification).data)
