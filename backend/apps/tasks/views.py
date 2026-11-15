from collections.abc import Mapping
from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import authenticated_user
from apps.accounts.models import User
from apps.core.schema import errors
from apps.tasks import selectors, services
from apps.tasks.models import Status
from apps.tasks.serializers import (
    TaskCreateSerializer,
    TaskFilterSerializer,
    TaskPageSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)
from apps.tasks.services import TaskChanges
from apps.teams.selectors import get_visible_team


class TaskPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _filters_from(request: Request) -> selectors.TaskFilters:
    params = TaskFilterSerializer(data=request.query_params)
    params.is_valid(raise_exception=True)
    data = params.validated_data
    assignee = data.get("assignee")
    return selectors.TaskFilters(
        team_id=data.get("team"),
        status=Status(data["status"]) if "status" in data else None,
        due_after=data.get("due_after"),
        due_before=data.get("due_before"),
        assignee_id=int(assignee) if assignee and assignee != "none" else None,
        unassigned=assignee == "none",
        overdue=data["overdue"],
        archived=data["archived"],
    )


def _changes_from(data: Mapping[str, object]) -> TaskChanges:
    """Only the fields present in the request; an explicit null clears assignee or due date."""
    changes = TaskChanges()
    if "title" in data:
        changes["title"] = str(data["title"])
    if "description" in data:
        changes["description"] = str(data["description"])
    if "status" in data:
        changes["status"] = Status(str(data["status"]))
    if "assignee" in data:
        assignee = data["assignee"]
        changes["assignee_id"] = assignee if isinstance(assignee, int) else None
    if "due_date" in data:
        due_date = data["due_date"]
        changes["due_date"] = due_date if isinstance(due_date, date) else None
    return changes


def _task_response(actor: User, task_id: int, http_status: int = status.HTTP_200_OK) -> Response:
    """The task as the actor sees it now, read again so the computed fields are current."""
    task = selectors.get_visible_task(actor, task_id)
    return Response(TaskSerializer(task, context={"viewer": actor}).data, status=http_status)


class TaskListView(APIView):
    @extend_schema(
        operation_id="tasks_list",
        parameters=[TaskFilterSerializer],
        responses={200: TaskPageSerializer, **errors(400)},
        description="Tasks of the caller's teams (all teams for admins), soonest due date first, "
        "no due date last. Archived tasks are left out unless `archived=true`.",
    )
    def get(self, request: Request) -> Response:
        actor = authenticated_user(request)
        tasks = selectors.list_tasks(actor, _filters_from(request))
        paginator = TaskPagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        data = TaskSerializer(page, many=True, context={"viewer": actor}).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        request=TaskCreateSerializer,
        responses={201: TaskSerializer, **errors(400, 403, 404)},
    )
    def post(self, request: Request) -> Response:
        actor = authenticated_user(request)
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = services.create_task(
            actor=actor,
            team=get_visible_team(actor, data["team"]),
            title=data["title"],
            description=data["description"],
            status=Status(data["status"]),
            assignee_id=data["assignee"],
            due_date=data["due_date"],
        )
        return _task_response(actor, task.pk, http_status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    @extend_schema(operation_id="tasks_retrieve", responses={200: TaskSerializer, **errors(404)})
    def get(self, request: Request, task_id: int) -> Response:
        return _task_response(authenticated_user(request), task_id)

    @extend_schema(
        request=TaskUpdateSerializer,
        responses={200: TaskSerializer, **errors(400, 403, 404)},
        description="Only the fields sent change; `null` clears the assignee or the due date. "
        "Finished tasks are read-only until reopened.",
    )
    def patch(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        task = selectors.get_visible_task(actor, task_id)
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.update_task(
            actor=actor, task=task, changes=_changes_from(serializer.validated_data)
        )
        return _task_response(actor, task_id)

    @extend_schema(responses={204: None, **errors(403, 404)})
    def delete(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        services.delete_task(actor=actor, task=selectors.get_visible_task(actor, task_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReopenTaskView(APIView):
    @extend_schema(
        request=None,
        responses={200: TaskSerializer, **errors(400, 403, 404)},
        description="Moves a done or canceled task back to in progress.",
    )
    def post(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        services.reopen_task(actor=actor, task=selectors.get_visible_task(actor, task_id))
        return _task_response(actor, task_id)


class AssignSelfView(APIView):
    @extend_schema(
        request=None,
        responses={200: TaskSerializer, **errors(400, 403, 404, 409)},
        description="A team member takes an unassigned, unfinished task.",
    )
    def post(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        services.assign_self(actor=actor, task=selectors.get_visible_task(actor, task_id))
        return _task_response(actor, task_id)
