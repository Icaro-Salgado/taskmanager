from collections.abc import Sequence

from django.contrib import admin
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest

from apps.accounts.auth import authenticated_user
from apps.core.admin import SuperuserOnlyAdminMixin
from apps.teams import selectors, services
from apps.teams.models import Membership, Role, Team


class OrphanTeamFilter(admin.SimpleListFilter):
    title = "leaders"
    parameter_name = "leaders"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Team]
    ) -> list[tuple[str, str]]:
        return [("none", "Without a leader (orphan)")]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Team]) -> QuerySet[Team]:
        if self.value() == "none":
            return queryset.exclude(memberships__role=Role.LEADER)
        return queryset


@admin.register(Team)
class TeamAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin[Team]):
    """Admins create and edit teams here. Deleting is a soft delete through the service."""

    list_display = ("name", "archive_after_days", "leader_count", "member_count", "created_at")
    list_filter = (OrphanTeamFilter,)
    search_fields = ("name",)
    fields = ("name", "archive_after_days")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Team]:
        return selectors.active_teams().annotate(
            leader_count=Count("memberships", filter=Q(memberships__role=Role.LEADER)),
            member_count=Count("memberships"),
        )

    @admin.display(description="Leaders", ordering="leader_count")
    def leader_count(self, team: Team) -> int:
        return int(getattr(team, "leader_count", 0))

    @admin.display(description="Members", ordering="member_count")
    def member_count(self, team: Team) -> int:
        return int(getattr(team, "member_count", 0))

    def get_deleted_objects(
        self, objs: Sequence[Team] | QuerySet[Team], request: HttpRequest
    ) -> tuple[list[str], dict[str, int], set[str], list[str]]:
        # A soft delete removes nothing else, so the confirmation page lists only the team.
        return [str(team) for team in objs], {"teams": len(objs)}, set(), []

    def delete_model(self, request: HttpRequest, obj: Team) -> None:
        services.delete_team(actor=authenticated_user(request), team=obj)


@admin.register(Membership)
class MembershipAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin[Membership]):
    """Adds, changes and removes go through the services, so their rules always run."""

    list_display = ("team", "user", "role", "created_at")
    list_filter = ("role", "team")
    search_fields = ("user__email", "team__name")
    list_select_related = ("team", "user")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Membership]:
        return super().get_queryset(request).filter(team__deleted_at__isnull=True)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Membership | None = None
    ) -> tuple[str, ...]:
        return ("team", "user") if obj else ()

    def save_model(self, request: HttpRequest, obj: Membership, form: object, change: bool) -> None:
        actor = authenticated_user(request)
        if change:
            services.change_role(actor=actor, membership=obj, role=Role(obj.role))
            return
        created = services.add_member(actor=actor, team=obj.team, email=obj.user.email)
        if obj.role == Role.LEADER:
            services.change_role(actor=actor, membership=created, role=Role.LEADER)
        obj.pk = created.pk  # the admin redirects and logs using this instance

    def delete_model(self, request: HttpRequest, obj: Membership) -> None:
        services.remove_member(actor=authenticated_user(request), membership=obj)
