import pytest

from apps.teams.tests.factories import TeamScenario, build_team_scenario


@pytest.fixture
def scenario(db: None) -> TeamScenario:
    return build_team_scenario()
