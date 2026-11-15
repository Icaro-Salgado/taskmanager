from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.http import HttpRequest

from apps.accounts.models import User
from apps.core.admin import SuperuserOnlyAdminMixin


class UserCreationForm(AdminUserCreationForm[User]):
    class Meta:
        model = User
        fields = ("email",)


class UserEditForm(UserChangeForm[User]):
    class Meta:
        model = User
        fields = ("email", "is_active", "is_staff", "is_superuser")


@admin.register(User)
class UserAdmin(SuperuserOnlyAdminMixin, DjangoUserAdmin[User]):
    """Users are deactivated, never deleted: their tasks and memberships stay for a reactivation."""

    form = UserEditForm
    add_form = UserCreationForm
    ordering = ("email",)
    list_display = ("email", "is_active", "is_superuser", "is_staff", "last_login")
    list_filter = ("is_active", "is_superuser", "is_staff")
    search_fields = ("email",)
    readonly_fields = ("last_login", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Access", {"fields": ("is_active", "is_superuser", "is_staff")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
    filter_horizontal = ()

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False
