import pytest
from django.db import IntegrityError, connection
from django.utils import timezone

from apps.teams.tests.factories import create_team

pytestmark = pytest.mark.django_db


def test_team_names_are_unique_among_active_teams_ignoring_case() -> None:
    create_team("Alpha")

    with pytest.raises(IntegrityError):
        create_team("ALPHA")


def test_a_deleted_team_frees_its_name() -> None:
    old = create_team("Alpha")
    old.deleted_at = timezone.now()
    old.save()

    assert create_team("Alpha").pk != old.pk


def test_restoring_a_team_fails_when_an_active_team_took_its_name() -> None:
    old = create_team("Alpha")
    old.deleted_at = timezone.now()
    old.save()
    create_team("Alpha")

    # The restore documented in the README: a plain SQL update.
    with pytest.raises(IntegrityError), connection.cursor() as cursor:
        cursor.execute(
            "UPDATE teams_team SET deleted_at = NULL, deleted_by_id = NULL WHERE id = %s",
            [old.pk],
        )


def test_archive_after_days_must_be_positive() -> None:
    with pytest.raises(IntegrityError):
        create_team("Alpha", archive_after_days=0)


def test_str_shows_the_name() -> None:
    assert str(create_team("Alpha")) == "Alpha"
