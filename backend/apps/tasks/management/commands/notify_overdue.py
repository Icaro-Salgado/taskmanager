from django.core.management.base import BaseCommand

from apps.tasks import services


class Command(BaseCommand):
    help = "Runs the daily overdue job now, without waiting for beat (on demand)."

    def handle(self, *_args: object, **_options: object) -> None:
        run = services.notify_overdue_tasks()
        self.stdout.write(
            f"Sent {run.notifications} notification(s) about {run.tasks} overdue task(s)."
        )
