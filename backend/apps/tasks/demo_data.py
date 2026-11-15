"""The content of the demo seed: who, which teams, which tasks. `seed_demo` turns it into rows."""

from dataclasses import dataclass

from apps.tasks.models import Status
from apps.teams.models import Role

# DEMO ONLY: this password is public and shared by every seeded account. Never use it outside a
# local demo database.
DEMO_PASSWORD = "Demo-only-pass-2026"  # noqa: S105
ADMIN_EMAIL = "admin@example.com"

ANA = "ana@example.com"
BRUNO = "bruno@example.com"
CARLA = "carla@example.com"
DIEGO = "diego@example.com"
EVA = "eva@example.com"
FABIO = "fabio@example.com"
GABI = "gabi@example.com"
USER_EMAILS = (ANA, BRUNO, CARLA, DIEGO, EVA, FABIO, GABI)

TODO = Status.TODO
DOING = Status.IN_PROGRESS
BLOCKED = Status.BLOCKED
DONE = Status.DONE
CANCELED = Status.CANCELED


@dataclass(frozen=True)
class TaskSpec:
    """Dates are offsets from today: `due` in days (negative is past), `finished` in days ago."""

    title: str
    status: Status
    assignee: str | None = None
    due: int | None = None
    finished: int = 0
    description: str = ""


@dataclass(frozen=True)
class TeamSpec:
    name: str
    archive_after_days: int
    members: dict[str, Role]  # email -> role
    tasks: tuple[TaskSpec, ...]
    deleted: bool = False


PLATFORM = TeamSpec(
    name="Platform",
    archive_after_days=15,
    members={ANA: Role.LEADER, BRUNO: Role.MEMBER, CARLA: Role.MEMBER, DIEGO: Role.MEMBER},
    # More than 20 active tasks, so the list paginates.
    tasks=(
        TaskSpec(
            "Upgrade PostgreSQL to 17",
            DOING,
            BRUNO,
            5,
            description="Rehearse the upgrade on staging first.",
        ),
        TaskSpec("Add rate limiting to the public API", DOING, ANA, 2),
        TaskSpec(
            "Rotate the staging database credentials",
            TODO,
            DIEGO,
            -3,
            description="Was due last week; the old ones are still valid.",
        ),
        TaskSpec("Write the incident runbook for failed deploys", TODO, CARLA, 10),
        TaskSpec(
            "Fix flaky integration test in billing",
            BLOCKED,
            BRUNO,
            -1,
            description="Waiting for a CI runner with more memory.",
        ),
        TaskSpec("Move the build cache to the shared runner", TODO, None, 14),
        TaskSpec("Document the on-call handover", TODO),
        TaskSpec("Replace the deprecated logging library", DOING, DIEGO, 7),
        TaskSpec("Set up error budget dashboards", TODO, CARLA, 21),
        TaskSpec(
            "Audit service account permissions",
            BLOCKED,
            ANA,
            -6,
            description="Needs the security team to export the access report.",
        ),
        TaskSpec("Reduce the Docker image size", DOING, None, 9),
        TaskSpec("Enable dependency vulnerability scanning", TODO, BRUNO, -10),
        TaskSpec("Plan the Redis failover test", TODO, DIEGO, 30),
        TaskSpec("Archive old build artifacts", TODO, None, 3),
        TaskSpec("Review the backup retention policy", TODO, ANA, 12),
        TaskSpec("Migrate the cron jobs to the scheduler", DOING, CARLA, 4),
        TaskSpec("Investigate the slow query on the reports page", BLOCKED, None, -2),
        TaskSpec("Publish the architecture overview", TODO, CARLA, 1),
        TaskSpec("Tune the database connection pool", TODO, None, -15),
        TaskSpec("Check TLS certificate expiry dates", DOING, ANA, 0),
        TaskSpec("Add health checks to the worker", DONE, BRUNO, finished=2),
        TaskSpec("Pin base image versions", DONE, DIEGO, finished=6),
        TaskSpec("Set up the staging environment", DONE, ANA, finished=40),
        TaskSpec("Remove unused feature flags", DONE, CARLA, finished=25),
        TaskSpec("Introduce structured logging", DONE, BRUNO, finished=60),
        TaskSpec(
            "Evaluate a second cloud region",
            CANCELED,
            None,
            finished=3,
            description="Out of budget this year.",
        ),
        TaskSpec("Switch to a managed Kafka", CANCELED, DIEGO, finished=45),
        TaskSpec("Rewrite the deploy script in Go", CANCELED, None, finished=90),
    ),
)

MOBILE = TeamSpec(
    name="Mobile App",
    archive_after_days=7,
    # Ana leads Platform but is only a member here.
    members={CARLA: Role.LEADER, ANA: Role.MEMBER, FABIO: Role.MEMBER},
    tasks=(
        TaskSpec("Fix the crash when opening a task offline", DOING, FABIO, 3),
        TaskSpec("Add dark mode to the task list", TODO, ANA, 15),
        TaskSpec("Support push notification deep links", BLOCKED, FABIO, -4),
        TaskSpec("Release 2.4 to the app stores", TODO, CARLA, 6),
        TaskSpec("Reduce startup time on older phones", TODO, None, 20),
        TaskSpec("Replace the date picker", DONE, ANA, finished=1),
        TaskSpec("Update the onboarding screens", DONE, FABIO, finished=12),
        TaskSpec("Drop support for Android 8", CANCELED, None, finished=20),
    ),
)

# No leader: nobody can manage its members, which the API must cope with.
DESIGN = TeamSpec(
    name="Design Guild",
    archive_after_days=15,
    members={EVA: Role.MEMBER, GABI: Role.MEMBER},
    tasks=(
        TaskSpec("Refresh the icon set", DOING, GABI, 8),
        TaskSpec("Write the accessibility checklist", TODO, EVA, -2),
        TaskSpec("Audit color contrast on the dashboard", TODO),
        TaskSpec("Publish the spacing guidelines", DONE, EVA, finished=5),
    ),
)

# Soft-deleted: its tasks still exist but must never show up in any list.
LEGACY = TeamSpec(
    name="Legacy Migration",
    archive_after_days=15,
    members={BRUNO: Role.LEADER, DIEGO: Role.MEMBER},
    tasks=(
        TaskSpec("Freeze writes to the old billing system", DONE, BRUNO, finished=50),
        TaskSpec("Decommission the old VPN", TODO, DIEGO, 30),
    ),
    deleted=True,
)

TEAMS = (PLATFORM, MOBILE, DESIGN, LEGACY)
