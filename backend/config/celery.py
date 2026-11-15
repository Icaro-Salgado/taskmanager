"""The Celery app used by the worker and beat (`celery -A config ...`).

Its settings are the CELERY_* names in `config.settings`. Each Django app keeps its Celery tasks in
a `tasks.py` module, found by autodiscovery.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
