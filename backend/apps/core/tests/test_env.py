from datetime import time

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import env_bool, env_int, env_list, env_str, env_time


def test_env_str_reads_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE", "value")

    assert env_str("SAMPLE") == "value"


def test_env_str_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAMPLE", raising=False)

    assert env_str("SAMPLE", "fallback") == "fallback"


@pytest.mark.parametrize("value", [None, ""])
def test_env_str_requires_a_value_when_there_is_no_default(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("SAMPLE", raising=False)
    else:
        monkeypatch.setenv("SAMPLE", value)

    with pytest.raises(ImproperlyConfigured, match="SAMPLE is required"):
        env_str("SAMPLE")


def test_env_int_parses_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE", "42")
    monkeypatch.delenv("MISSING", raising=False)

    assert env_int("SAMPLE") == 42
    assert env_int("MISSING", 7) == 7


def test_env_int_rejects_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE", "abc")

    with pytest.raises(ImproperlyConfigured, match="must be an integer"):
        env_int("SAMPLE")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", True), ("True", True), ("yes", True), ("0", False), ("false", False), ("OFF", False)],
)
def test_env_bool_parses_common_spellings(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("SAMPLE", raw)

    assert env_bool("SAMPLE", default=not expected) is expected


def test_env_bool_defaults_and_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING", raising=False)
    monkeypatch.setenv("SAMPLE", "maybe")

    assert env_bool("MISSING", default=True) is True
    with pytest.raises(ImproperlyConfigured, match="must be a boolean"):
        env_bool("SAMPLE", default=False)


def test_env_list_splits_and_trims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE", "a, b ,,c")
    monkeypatch.delenv("MISSING", raising=False)

    assert env_list("SAMPLE", default="") == ["a", "b", "c"]
    assert env_list("MISSING", default="") == []


def test_env_time_parses_hours_and_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE", "18:30")
    monkeypatch.delenv("MISSING", raising=False)

    assert env_time("SAMPLE", "08:00") == time(18, 30)
    assert env_time("MISSING", "08:00") == time(8, 0)


def test_env_time_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE", "8 o'clock")

    with pytest.raises(ImproperlyConfigured, match="must be a time as HH:MM"):
        env_time("SAMPLE", "08:00")
