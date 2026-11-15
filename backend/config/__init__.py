# Loaded with Django, so `@shared_task` functions bind to this app in the api process too.
from config.celery import app as celery_app

__all__ = ("celery_app",)
