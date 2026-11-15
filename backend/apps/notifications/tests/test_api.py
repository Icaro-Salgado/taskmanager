from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.tests.factories import client_for
from apps.notifications.models import Notification
from apps.teams.tests.factories import TeamScenario

NOTIFICATIONS_URL = "/api/v1/notifications"


def read_url(notification: Notification) -> str:
    return f"{NOTIFICATIONS_URL}/{notification.pk}/read"


def notify(scenario: TeamScenario, message: str = "Hello") -> Notification:
    return Notification.objects.create(user=scenario.member, team=scenario.team, message=message)


def test_notifications_require_authentication(
    api_client: APIClient, scenario: TeamScenario
) -> None:
    notification = notify(scenario)

    assert api_client.get(NOTIFICATIONS_URL).status_code == 401
    assert api_client.post(read_url(notification)).status_code == 401


def test_the_list_returns_the_callers_notifications(scenario: TeamScenario) -> None:
    notification = notify(scenario)
    Notification.objects.create(user=scenario.leader, team=scenario.team, message="Not yours")

    response = client_for(scenario.member).get(NOTIFICATIONS_URL)

    assert response.status_code == 200
    body = response.json()
    assert (body["count"], body["next"], body["previous"]) == (1, None, None)
    item = body["results"][0]
    assert set(item) == {"id", "team", "task", "message", "created_at", "read_at"}
    assert (item["id"], item["team"], item["task"]) == (notification.pk, scenario.team.pk, None)
    assert (item["message"], item["read_at"]) == ("Hello", None)


def test_the_unread_filter(scenario: TeamScenario) -> None:
    unread = notify(scenario, "unread")
    read = notify(scenario, "read")
    client = client_for(scenario.member)
    client.post(read_url(read))

    everything = client.get(NOTIFICATIONS_URL).json()["results"]
    only_unread = client.get(NOTIFICATIONS_URL, {"unread": "true"}).json()["results"]

    assert [item["id"] for item in everything] == [read.pk, unread.pk]
    assert [item["id"] for item in only_unread] == [unread.pk]


def test_an_invalid_unread_value_answers_400(scenario: TeamScenario) -> None:
    response = client_for(scenario.member).get(NOTIFICATIONS_URL, {"unread": "maybe"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid"


def test_the_list_is_paginated_with_a_maximum_page_size(scenario: TeamScenario) -> None:
    Notification.objects.bulk_create(
        Notification(user=scenario.member, team=scenario.team, message=f"n{index}")
        for index in range(105)
    )
    client = client_for(scenario.member)

    default_page = client.get(NOTIFICATIONS_URL).json()
    capped_page = client.get(NOTIFICATIONS_URL, {"page_size": 500}).json()

    assert (default_page["count"], len(default_page["results"])) == (105, 20)
    assert default_page["next"] is not None
    assert len(capped_page["results"]) == 100


def test_mark_read_answers_the_item_and_is_idempotent(scenario: TeamScenario) -> None:
    notification = notify(scenario)
    client = client_for(scenario.member)

    first = client.post(read_url(notification))
    second = client.post(read_url(notification))

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == notification.pk
    assert first.json()["read_at"] is not None
    assert second.json()["read_at"] == first.json()["read_at"]


def test_someone_elses_notification_answers_404(scenario: TeamScenario) -> None:
    notification = notify(scenario)

    response = client_for(scenario.leader).post(read_url(notification))

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    notification.refresh_from_db()
    assert notification.read_at is None


def test_list_queries_do_not_grow_with_the_number_of_notifications(
    scenario: TeamScenario,
) -> None:
    client = client_for(scenario.member)
    notify(scenario)
    with CaptureQueriesContext(connection) as few:
        client.get(NOTIFICATIONS_URL)
    for index in range(10):
        notify(scenario, f"n{index}")

    with CaptureQueriesContext(connection) as many:
        client.get(NOTIFICATIONS_URL)

    assert len(many) == len(few) == 2  # one count for the pagination, one page
