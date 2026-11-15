from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import authenticated_user
from apps.core.schema import errors
from apps.teams import selectors, services
from apps.teams.models import Role
from apps.teams.serializers import (
    AddMemberSerializer,
    ChangeRoleSerializer,
    MemberSerializer,
    TeamSerializer,
)


class TeamListView(APIView):
    @extend_schema(
        operation_id="teams_list",
        responses={200: TeamSerializer(many=True), **errors()},
        description="Teams the caller belongs to; admins see every team.",
    )
    def get(self, request: Request) -> Response:
        teams = selectors.teams_visible_to(authenticated_user(request))
        return Response(TeamSerializer(teams, many=True).data)


class TeamDetailView(APIView):
    @extend_schema(operation_id="teams_retrieve", responses={200: TeamSerializer, **errors(404)})
    def get(self, request: Request, team_id: int) -> Response:
        team = selectors.get_visible_team(authenticated_user(request), team_id)
        return Response(TeamSerializer(team).data)


class MemberListView(APIView):
    @extend_schema(responses={200: MemberSerializer(many=True), **errors(404)})
    def get(self, request: Request, team_id: int) -> Response:
        team = selectors.get_visible_team(authenticated_user(request), team_id)
        return Response(MemberSerializer(selectors.members_of(team), many=True).data)

    @extend_schema(
        request=AddMemberSerializer,
        responses={201: MemberSerializer, **errors(400, 403, 404, 409)},
        description="Leaders and admins add an active user by email, as a member.",
    )
    def post(self, request: Request, team_id: int) -> Response:
        actor = authenticated_user(request)
        team = selectors.get_visible_team(actor, team_id)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_member(
            actor=actor, team=team, email=serializer.validated_data["email"]
        )
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    @extend_schema(
        request=ChangeRoleSerializer,
        responses={200: MemberSerializer, **errors(400, 403, 404)},
    )
    def patch(self, request: Request, team_id: int, user_id: int) -> Response:
        actor = authenticated_user(request)
        membership = selectors.get_membership(selectors.get_visible_team(actor, team_id), user_id)
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.change_role(
            actor=actor, membership=membership, role=Role(serializer.validated_data["role"])
        )
        return Response(MemberSerializer(membership).data)

    @extend_schema(
        responses={204: None, **errors(403, 404)},
        description="Leaders remove a member, or a member leaves. Their tasks in the team are "
        "unassigned in the same transaction.",
    )
    def delete(self, request: Request, team_id: int, user_id: int) -> Response:
        actor = authenticated_user(request)
        membership = selectors.get_membership(selectors.get_visible_team(actor, team_id), user_id)
        services.remove_member(actor=actor, membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)
