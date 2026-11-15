from collections.abc import Mapping
from datetime import date

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import authenticated_user
from apps.tasks import selectors, services
from apps.tasks.models import Status
from apps.tasks.serializers import (
    TaskCreateSerializer,
    TaskFilterSerializer,
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


class TaskListView(APIView):
    def get(self, request: Request) -> Response:
        tasks = selectors.list_tasks(authenticated_user(request), _filters_from(request))
        paginator = TaskPagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        return paginator.get_paginated_response(TaskSerializer(page, many=True).data)

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
        task = selectors.get_visible_task(actor, task.pk)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    def get(self, request: Request, task_id: int) -> Response:
        task = selectors.get_visible_task(authenticated_user(request), task_id)
        return Response(TaskSerializer(task).data)

    def patch(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        task = selectors.get_visible_task(actor, task_id)
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.update_task(
            actor=actor, task=task, changes=_changes_from(serializer.validated_data)
        )
        return Response(TaskSerializer(selectors.get_visible_task(actor, task_id)).data)

    def delete(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        services.delete_task(actor=actor, task=selectors.get_visible_task(actor, task_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReopenTaskView(APIView):
    def post(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        services.reopen_task(actor=actor, task=selectors.get_visible_task(actor, task_id))
        return Response(TaskSerializer(selectors.get_visible_task(actor, task_id)).data)


class AssignSelfView(APIView):
    def post(self, request: Request, task_id: int) -> Response:
        actor = authenticated_user(request)
        services.assign_self(actor=actor, task=selectors.get_visible_task(actor, task_id))
        return Response(TaskSerializer(selectors.get_visible_task(actor, task_id)).data)
