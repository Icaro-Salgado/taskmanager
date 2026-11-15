from django.urls import path

from apps.teams.views import MemberDetailView, MemberListView, TeamDetailView, TeamListView

urlpatterns = [
    path("teams", TeamListView.as_view(), name="team-list"),
    path("teams/<int:team_id>", TeamDetailView.as_view(), name="team-detail"),
    path("teams/<int:team_id>/members", MemberListView.as_view(), name="member-list"),
    path(
        "teams/<int:team_id>/members/<int:user_id>",
        MemberDetailView.as_view(),
        name="member-detail",
    ),
]
