from django.db import models


class TimestampedModel(models.Model):
    """Base for every model: when the row was created and last changed."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
