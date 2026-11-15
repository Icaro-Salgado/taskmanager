"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.teams.urls")),
    path("api/v1/", include("apps.tasks.urls")),
]

# Used when DEBUG is off; with DEBUG on, Django shows its technical 404 page instead.
handler404 = "apps.core.views.not_found"
