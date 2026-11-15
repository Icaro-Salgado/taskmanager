from django.contrib import admin
from django.http import HttpRequest

from apps.core.admin import is_admin_request
from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin[Task]):
    """Read-only: tasks change only through the API, where the services enforce their rules."""

    list_display = ("title", "team", "status", "assignee", "due_date", "completed_at", "deleted_at")
    list_filter = ("status", "team")
    search_fields = ("title", "team__name", "assignee__email")
    list_select_related = ("team", "assignee")

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_admin_request(request)

    def has_view_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return is_admin_request(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False
