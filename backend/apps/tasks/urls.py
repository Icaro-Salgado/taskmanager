from django.urls import path

from apps.tasks.views import AssignSelfView, ReopenTaskView, TaskDetailView, TaskListView

urlpatterns = [
    path("tasks", TaskListView.as_view(), name="task-list"),
    path("tasks/<int:task_id>", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:task_id>/reopen", ReopenTaskView.as_view(), name="task-reopen"),
    path("tasks/<int:task_id>/assign-self", AssignSelfView.as_view(), name="task-assign-self"),
]
