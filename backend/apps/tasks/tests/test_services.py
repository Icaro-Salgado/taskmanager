from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.tests.factories import create_user
from apps.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
)
from apps.tasks import services
from apps.tasks.models import Status, Task
from apps.tasks.tests.factories import create_task
from apps.teams import services as team_services
from apps.teams.models import Membership
from apps.teams.tests.factories import TeamScenario, add_membership, create_team


@pytest.fixture
def other(scenario: TeamScenario) -> User:
    """A second plain member, who neither created nor is assigned the task."""
    user = create_user("other@example.com")
    add_membership(scenario.team, user)
    return user


@pytest.fixture
def assignee(scenario: TeamScenario) -> User:
    user = create_user("assignee@example.com")
    add_membership(scenario.team, user)
    return user


@pytest.fixture
def task(scenario: TeamScenario, assignee: User) -> Task:
    """Created by the member, assigned to `assignee`."""
    return create_task(scenario.team, scenario.member, assignee=assignee)


def actor(name: str, scenario: TeamScenario, assignee: User, other: User) -> User:
    users = {
        "admin": scenario.admin,
        "leader": scenario.leader,
        "creator": scenario.member,
        "assignee": assignee,
        "other member": other,
        "outsider": scenario.outsider,
    }
    return users[name]


# --- Permission matrix ------------------------------------------------------------------------

EDIT_MATRIX = [
    ("admin", True),
    ("leader", True),
    ("creator", True),
    ("assignee", True),
    ("other member", False),
    ("outsider", False),
]
DELETE_MATRIX = [
    ("admin", True),
    ("leader", True),
    ("creator", True),
    ("assignee", False),
    ("other member", False),
    ("outsider", False),
]


@pytest.mark.parametrize(("who", "allowed"), EDIT_MATRIX)
def test_who_may_edit_a_task(
    scenario: TeamScenario, assignee: User, other: User, task: Task, who: str, allowed: bool
) -> None:
    user = actor(who, scenario, assignee, other)
    if allowed:
        assert services.update_task(actor=user, task=task, changes={"title": "E"}).title == "E"
    else:
        with pytest.raises(PermissionDeniedError):
            services.update_task(actor=user, task=task, changes={"title": "E"})


@pytest.mark.parametrize(("who", "allowed"), EDIT_MATRIX)
def test_who_may_reopen_a_task(
    scenario: TeamScenario, assignee: User, other: User, who: str, allowed: bool
) -> None:
    done = create_task(scenario.team, scenario.member, assignee=assignee, status=Status.DONE)
    user = actor(who, scenario, assignee, other)
    if allowed:
        assert services.reopen_task(actor=user, task=done).status == Status.IN_PROGRESS
    else:
        with pytest.raises(PermissionDeniedError):
            services.reopen_task(actor=user, task=done)


@pytest.mark.parametrize(("who", "allowed"), DELETE_MATRIX)
def test_who_may_delete_a_task(
    scenario: TeamScenario, assignee: User, other: User, task: Task, who: str, allowed: bool
) -> None:
    user = actor(who, scenario, assignee, other)
    if allowed:
        services.delete_task(actor=user, task=task)
        task.refresh_from_db()
        assert task.deleted_at is not None
    else:
        with pytest.raises(PermissionDeniedError):
            services.delete_task(actor=user, task=task)


def test_a_creator_who_left_the_team_has_no_rights_on_their_task(
    scenario: TeamScenario, task: Task
) -> None:
    Membership.objects.filter(team=scenario.team, user=scenario.member).delete()

    with pytest.raises(PermissionDeniedError):
        services.update_task(actor=scenario.member, task=task, changes={"title": "Mine"})
    with pytest.raises(PermissionDeniedError):
        services.delete_task(actor=scenario.member, task=task)


# --- Create -----------------------------------------------------------------------------------


def test_any_member_creates_a_task_in_their_team(scenario: TeamScenario) -> None:
    task = services.create_task(actor=scenario.member, team=scenario.team, title="Write docs")

    assert (task.status, task.created_by, task.assignee) == (Status.TODO, scenario.member, None)


def test_an_admin_creates_a_task_in_any_team(scenario: TeamScenario) -> None:
    services.create_task(actor=scenario.admin, team=scenario.team, title="From admin")


def test_outsiders_cannot_create_tasks(scenario: TeamScenario) -> None:
    with pytest.raises(PermissionDeniedError):
        services.create_task(actor=scenario.outsider, team=scenario.team, title="Nope")


@pytest.mark.parametrize("status", [Status.DONE, Status.CANCELED])
def test_a_task_cannot_be_created_finished(scenario: TeamScenario, status: Status) -> None:
    with pytest.raises(RuleViolationError) as error:
        services.create_task(actor=scenario.member, team=scenario.team, title="T", status=status)

    assert error.value.code == "terminal_on_create"


def test_tasks_cannot_be_created_in_a_deleted_team(scenario: TeamScenario) -> None:
    team_services.delete_team(actor=scenario.admin, team=scenario.team)

    with pytest.raises(NotFoundError):
        services.create_task(actor=scenario.admin, team=scenario.team, title="T")


# --- The assignee invariant -------------------------------------------------------------------


def test_the_assignee_can_be_any_member(scenario: TeamScenario, other: User) -> None:
    task = services.create_task(
        actor=scenario.member, team=scenario.team, title="T", assignee_id=other.pk
    )

    assert task.assignee == other


def test_the_assignee_must_be_a_member_of_the_team(scenario: TeamScenario) -> None:
    with pytest.raises(RuleViolationError) as error:
        services.create_task(
            actor=scenario.leader, team=scenario.team, title="T", assignee_id=scenario.outsider.pk
        )

    assert error.value.code == "invalid_assignee"


def test_a_member_of_another_team_cannot_be_assigned(scenario: TeamScenario, task: Task) -> None:
    stranger = create_user("stranger@example.com")
    add_membership(create_team("Beta"), stranger)

    with pytest.raises(RuleViolationError):
        services.update_task(actor=scenario.leader, task=task, changes={"assignee_id": stranger.pk})


def test_an_inactive_member_cannot_be_picked_as_a_new_assignee(
    scenario: TeamScenario, task: Task, other: User
) -> None:
    User.objects.filter(pk=other.pk).update(is_active=False)

    with pytest.raises(RuleViolationError):
        services.update_task(actor=scenario.leader, task=task, changes={"assignee_id": other.pk})


def test_a_deactivated_assignee_keeps_the_task_when_other_fields_change(
    scenario: TeamScenario, task: Task, assignee: User
) -> None:
    User.objects.filter(pk=assignee.pk).update(is_active=False)

    edited = services.update_task(
        actor=scenario.leader,
        task=task,
        changes={"title": "Still theirs", "assignee_id": assignee.pk},
    )

    assert edited.assignee_id == assignee.pk


def test_clearing_the_assignee(scenario: TeamScenario, task: Task) -> None:
    edited = services.update_task(actor=scenario.leader, task=task, changes={"assignee_id": None})

    assert edited.assignee is None


def test_removing_a_member_unassigns_their_tasks_in_that_team_only(
    scenario: TeamScenario, task: Task, assignee: User
) -> None:
    beta = create_team("Beta")
    add_membership(beta, assignee)
    elsewhere = create_task(beta, assignee, assignee=assignee)
    deleted = create_task(scenario.team, scenario.member, assignee=assignee)
    services.delete_task(actor=scenario.leader, task=deleted)
    membership = Membership.objects.get(team=scenario.team, user=assignee)

    team_services.remove_member(actor=scenario.leader, membership=membership)

    task.refresh_from_db()
    deleted.refresh_from_db()
    elsewhere.refresh_from_db()
    assert (task.assignee, deleted.assignee, elsewhere.assignee) == (None, None, assignee)


def test_member_removal_and_unassignment_happen_in_one_transaction(
    scenario: TeamScenario, task: Task, assignee: User
) -> None:
    membership = Membership.objects.get(team=scenario.team, user=assignee)

    with (
        patch.object(Membership, "delete", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        team_services.remove_member(actor=scenario.leader, membership=membership)

    task.refresh_from_db()
    assert task.assignee == assignee  # the unassignment was rolled back


def test_removing_a_member_who_was_already_removed_answers_not_found(
    scenario: TeamScenario, other: User
) -> None:
    membership = Membership.objects.get(team=scenario.team, user=other)
    Membership.objects.filter(pk=membership.pk).delete()  # another request got there first

    with pytest.raises(NotFoundError):
        team_services.remove_member(actor=scenario.leader, membership=membership)


def test_assignment_and_member_removal_lock_the_membership_row(
    scenario: TeamScenario, task: Task, other: User
) -> None:
    """Both sides take the same row lock: neither slips between the other's check and write."""
    membership = Membership.objects.get(team=scenario.team, user=other)

    with CaptureQueriesContext(connection) as assigning:
        services.update_task(actor=scenario.leader, task=task, changes={"assignee_id": other.pk})
    with CaptureQueriesContext(connection) as removing:
        team_services.remove_member(actor=scenario.leader, membership=membership)

    for queries in (assigning, removing):
        assert any(
            "teams_membership" in query["sql"] and "FOR UPDATE" in query["sql"]
            for query in queries.captured_queries
        )


# --- Status, terminal and reopen --------------------------------------------------------------


def test_non_terminal_statuses_move_freely(scenario: TeamScenario, task: Task) -> None:
    for status in (Status.BLOCKED, Status.IN_PROGRESS, Status.TODO, Status.BLOCKED):
        task = services.update_task(actor=scenario.leader, task=task, changes={"status": status})
        assert (task.status, task.completed_at) == (status, None)


@pytest.mark.parametrize("status", [Status.DONE, Status.CANCELED])
def test_finishing_a_task_sets_completed_at(
    scenario: TeamScenario, task: Task, status: Status
) -> None:
    finished = services.update_task(actor=scenario.leader, task=task, changes={"status": status})

    assert finished.completed_at is not None


@pytest.mark.parametrize("status", [Status.DONE, Status.CANCELED])
def test_finished_tasks_are_read_only(scenario: TeamScenario, status: Status) -> None:
    finished = create_task(scenario.team, scenario.member, status=status)

    with pytest.raises(RuleViolationError) as error:
        services.update_task(actor=scenario.leader, task=finished, changes={"title": "Again"})

    assert error.value.code == "task_finished"


def test_finished_tasks_can_still_be_deleted(scenario: TeamScenario) -> None:
    finished = create_task(scenario.team, scenario.member, status=Status.DONE)

    services.delete_task(actor=scenario.leader, task=finished)


def test_reopen_moves_to_in_progress_and_clears_the_dates(scenario: TeamScenario) -> None:
    finished = create_task(scenario.team, scenario.member, status=Status.CANCELED)
    Task.objects.filter(pk=finished.pk).update(overdue_notified_at=timezone.now())
    finished.refresh_from_db()

    reopened = services.reopen_task(actor=scenario.leader, task=finished)

    assert (reopened.status, reopened.completed_at, reopened.overdue_notified_at) == (
        Status.IN_PROGRESS,
        None,
        None,
    )


def test_only_finished_tasks_can_be_reopened(scenario: TeamScenario, task: Task) -> None:
    with pytest.raises(RuleViolationError) as error:
        services.reopen_task(actor=scenario.leader, task=task)

    assert error.value.code == "task_not_finished"


def test_changing_the_due_date_clears_the_overdue_notification(
    scenario: TeamScenario, task: Task
) -> None:
    Task.objects.filter(pk=task.pk).update(overdue_notified_at=timezone.now())
    task.refresh_from_db()
    later = timezone.localdate() + timedelta(days=3)

    same = services.update_task(actor=scenario.leader, task=task, changes={"due_date": None})
    assert same.overdue_notified_at is not None  # unchanged due date (still empty)
    moved = services.update_task(actor=scenario.leader, task=task, changes={"due_date": later})

    assert moved.overdue_notified_at is None


# --- Assign self ------------------------------------------------------------------------------


def test_a_member_takes_an_unassigned_task_and_nothing_else_changes(
    scenario: TeamScenario, other: User
) -> None:
    open_task = create_task(scenario.team, scenario.leader, title="Free", status=Status.BLOCKED)

    taken = services.assign_self(actor=other, task=open_task)

    assert (taken.assignee, taken.title, taken.status) == (other, "Free", Status.BLOCKED)


def test_an_assigned_task_cannot_be_taken(scenario: TeamScenario, task: Task, other: User) -> None:
    with pytest.raises(ConflictError):
        services.assign_self(actor=other, task=task)


def test_two_members_taking_the_same_task_only_the_first_wins(
    scenario: TeamScenario, other: User
) -> None:
    open_task = create_task(scenario.team, scenario.leader)
    stale = Task.objects.select_related("team").get(pk=open_task.pk)  # read before the first take

    services.assign_self(actor=other, task=open_task)
    with pytest.raises(ConflictError):
        services.assign_self(actor=scenario.member, task=stale)

    open_task.refresh_from_db()
    assert open_task.assignee == other


def test_an_admin_who_is_not_a_member_cannot_take_a_task(scenario: TeamScenario) -> None:
    open_task = create_task(scenario.team, scenario.leader)

    with pytest.raises(PermissionDeniedError):
        services.assign_self(actor=scenario.admin, task=open_task)


def test_a_finished_task_cannot_be_taken(scenario: TeamScenario, other: User) -> None:
    finished = create_task(scenario.team, scenario.leader, status=Status.DONE)

    with pytest.raises(RuleViolationError):
        services.assign_self(actor=other, task=finished)


# --- Soft delete ------------------------------------------------------------------------------


def test_delete_is_soft_and_a_deleted_task_cannot_be_changed(
    scenario: TeamScenario, task: Task
) -> None:
    services.delete_task(actor=scenario.leader, task=task)

    task.refresh_from_db()
    assert task.deleted_by == scenario.leader
    with pytest.raises(NotFoundError):
        services.update_task(actor=scenario.admin, task=task, changes={"title": "Ghost"})
