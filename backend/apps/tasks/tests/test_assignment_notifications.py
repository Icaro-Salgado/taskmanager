from datetime import timedelta

from django.utils import timezone
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks as CaptureCallbacks

from apps.accounts.models import User
from apps.accounts.tests.factories import client_for, create_user
from apps.notifications.models import Notification
from apps.tasks import services
from apps.tasks.models import Task
from apps.tasks.tests.factories import create_task
from apps.teams.tests.factories import TeamScenario, add_membership


def messages_of(user: User) -> list[str]:
    return list(
        Notification.objects.filter(user=user).order_by("id").values_list("message", flat=True)
    )


def assign(actor: User, task: Task, assignee: User | None) -> Task:
    return services.update_task(
        actor=actor, task=task, changes={"assignee_id": assignee.pk if assignee else None}
    )


def test_assigning_someone_else_notifies_them_after_the_commit(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    task = create_task(scenario.team, scenario.leader, title="Ship it")

    with django_capture_on_commit_callbacks() as callbacks:
        assign(scenario.leader, task, scenario.member)
    assert messages_of(scenario.member) == []  # nothing before the commit

    for callback in callbacks:
        callback()

    assert messages_of(scenario.member) == ['You were assigned task "Ship it".']
    notification = Notification.objects.get(user=scenario.member)
    assert (notification.team_id, notification.task_id) == (scenario.team.pk, task.pk)


def test_creating_a_task_for_someone_else_notifies_them(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        services.create_task(
            actor=scenario.leader, team=scenario.team, title="New", assignee_id=scenario.member.pk
        )

    assert messages_of(scenario.member) == ['You were assigned task "New".']


def test_assigning_yourself_sends_nothing(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        task = services.create_task(
            actor=scenario.member, team=scenario.team, title="Mine", assignee_id=scenario.member.pk
        )
        assign(scenario.leader, task, None)
        assign(scenario.leader, task, scenario.leader)
        services.assign_self(
            actor=scenario.member, task=create_task(scenario.team, scenario.leader)
        )

    assert callbacks == []
    assert not Notification.objects.exists()


def test_keeping_the_same_assignee_sends_nothing(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    task = create_task(scenario.team, scenario.leader, assignee=scenario.member)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        assign(scenario.leader, task, scenario.member)

    assert callbacks == []


def test_an_overdue_task_says_so(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    task = create_task(
        scenario.team, scenario.leader, title="Late", due_date=timezone.localdate() - timedelta(1)
    )

    with django_capture_on_commit_callbacks(execute=True):
        assign(scenario.leader, task, scenario.member)

    assert messages_of(scenario.member) == ['You were assigned task "Late", which is overdue.']


def test_a_task_the_job_already_notified_is_not_notified_again(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    newcomer = create_user("newcomer@example.com")
    add_membership(scenario.team, newcomer)
    task = create_task(
        scenario.team,
        scenario.leader,
        title="Late",
        assignee=scenario.member,
        due_date=timezone.localdate() - timedelta(1),
    )
    services.notify_overdue_tasks()
    task.refresh_from_db()
    notified_at = task.overdue_notified_at

    with django_capture_on_commit_callbacks(execute=True):
        assign(scenario.leader, task, newcomer)
    rerun = services.notify_overdue_tasks()

    assert messages_of(newcomer) == ['You were assigned task "Late", which is overdue.']
    assert rerun.notifications == 0
    task.refresh_from_db()
    assert task.overdue_notified_at == notified_at


def test_nothing_is_sent_for_a_task_deleted_or_reassigned_before_the_worker_runs(
    scenario: TeamScenario,
) -> None:
    reassigned = create_task(scenario.team, scenario.leader, assignee=scenario.leader)
    deleted = create_task(scenario.team, scenario.leader, assignee=scenario.member)
    Task.objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())

    for task in (reassigned, deleted):
        sent = services.send_assignment_notification(
            task_id=task.pk, assignee_id=scenario.member.pk
        )
        assert sent is None
    assert not Notification.objects.exists()


def test_the_new_assignee_reads_it_through_the_api(
    scenario: TeamScenario, django_capture_on_commit_callbacks: CaptureCallbacks
) -> None:
    task = create_task(scenario.team, scenario.leader, title="Ship it")

    with django_capture_on_commit_callbacks(execute=True):
        response = client_for(scenario.leader).patch(
            f"/api/v1/tasks/{task.pk}", {"assignee": scenario.member.pk}, format="json"
        )
    assert response.status_code == 200

    results = client_for(scenario.member).get("/api/v1/notifications").json()["results"]
    assert [(item["task"], item["message"]) for item in results] == [
        (task.pk, 'You were assigned task "Ship it".')
    ]
