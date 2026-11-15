"""Typed readers for environment variables. Settings read every value through these."""

import os
from datetime import time

from django.core.exceptions import ImproperlyConfigured

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def env_str(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise ImproperlyConfigured(f"Environment variable {name} is required.")
    return value


def env_int(name: str, default: int | None = None) -> int:
    raw = env_str(name, None if default is None else str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"Environment variable {name} must be an integer.") from exc


def env_bool(name: str, default: bool) -> bool:
    raw = env_str(name, str(default)).strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ImproperlyConfigured(f"Environment variable {name} must be a boolean.")


def env_list(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_time(name: str, default: str) -> time:
    """A time of day written as HH:MM, for example 08:00."""
    raw = env_str(name, default)
    try:
        return time.fromisoformat(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"Environment variable {name} must be a time as HH:MM.") from exc
