import pytest

from apps.accounts.tests.factories import create_user
from apps.core.exceptions import NotFoundError
from apps.notifications import selectors, services
from apps.notifications.models import Notification
from apps.teams.tests.factories import TeamScenario


def notify(scenario: TeamScenario, message: str = "Hello") -> Notification:
    notification = services.create_notification(
        user=scenario.member, team=scenario.team, message=message
    )
    assert notification is not None
    return notification


def test_create_stores_the_notification_unread(scenario: TeamScenario) -> None:
    notification = notify(scenario)

    assert (notification.user, notification.team) == (scenario.member, scenario.team)
    assert (notification.task_id, notification.read_at) == (None, None)


def test_a_deactivated_user_receives_no_notifications(scenario: TeamScenario) -> None:
    inactive = create_user("gone@example.com", is_active=False)

    created = services.create_notification(user=inactive, team=scenario.team, message="Hi")

    assert created is None
    assert not Notification.objects.filter(user=inactive).exists()


def test_mark_read_is_idempotent(scenario: TeamScenario) -> None:
    notification = notify(scenario)

    first = services.mark_read(user=scenario.member, notification_id=notification.pk)
    second = services.mark_read(user=scenario.member, notification_id=notification.pk)

    assert first.read_at is not None
    assert second.read_at == first.read_at


def test_nobody_else_can_mark_a_notification_read(scenario: TeamScenario) -> None:
    notification = notify(scenario)

    with pytest.raises(NotFoundError):
        services.mark_read(user=scenario.leader, notification_id=notification.pk)


def test_a_user_lists_only_their_own_notifications_newest_first(scenario: TeamScenario) -> None:
    older = notify(scenario, "older")
    newer = notify(scenario, "newer")
    services.create_notification(user=scenario.leader, team=scenario.team, message="not yours")

    assert list(selectors.notifications_of(scenario.member)) == [newer, older]


def test_the_unread_filter_leaves_out_read_notifications(scenario: TeamScenario) -> None:
    read = notify(scenario, "read")
    unread = notify(scenario, "unread")
    services.mark_read(user=scenario.member, notification_id=read.pk)

    assert list(selectors.notifications_of(scenario.member, unread_only=True)) == [unread]
