from django.contrib import admin
from django.http import HttpRequest

# The bulk "delete selected" action calls QuerySet.delete(), which would skip the services (teams,
# memberships) or delete what must never be deleted (users). It is turned off for the whole site.
admin.site.disable_action("delete_selected")


def is_admin_request(request: HttpRequest) -> bool:
    """Only global admins (superusers) manage data in the admin site; staff can only log in."""
    return bool(getattr(request.user, "is_superuser", False))


class SuperuserOnlyAdminMixin:
    """Restricts a ModelAdmin to superusers, so every change through it passes the admin policy."""

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_admin_request(request)

    def has_view_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return is_admin_request(request)

    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return is_admin_request(request)

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return is_admin_request(request)

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return is_admin_request(request)
