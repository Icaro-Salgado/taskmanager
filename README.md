# Task manager

A task management system for teams: a Django REST API, a React frontend, and background jobs for notifications.

# Part 1: Setup and instructions

## Prerequisites

- Docker with Docker Compose v2 (`docker compose`). Nothing else is needed to run the app.
- Only for working on the code outside Docker: Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node.js 24.

## Usage

```sh
./run.sh up              # build and start everything, with the demo data (the default command)
./run.sh up --no-seed    # same, without loading the demo data
./run.sh down            # stop (the database volume is kept)
./run.sh test            # backend tests with coverage
```

On Windows: `.\run.ps1 up`, `.\run.ps1 up -NoSeed`, `.\run.ps1 down`, `.\run.ps1 test` (untested).

Then open http://localhost:8080/ (API docs: http://localhost:8080/api/v1/docs).

## Documentation

- [`docs/running.md`](docs/running.md): what the script does, URLs, database access, tests, development.
- [`seed/README.md`](seed/README.md): demo accounts (demo-only credentials) and the sample data.
- [`GENAI.md`](GENAI.md): how the project was built with a GenAI tool.
- [`docs/requirements.md`](docs/requirements.md), [`docs/implementation-prompt.md`](docs/implementation-prompt.md),
  [`docs/backlog.md`](docs/backlog.md).

# Part 2: User story and design

## Who uses it

The requirements say tasks are assigned to users, but not who may see a task or assign it to whom. Teams with two
roles are the smallest model that answers that: people see and assign tasks inside their own teams.

- **A team member** opens the board of their team: one column per status (to do, in progress, blocked, done,
  canceled). They create tasks, take an unassigned task, move tasks through their statuses from the card, and
  filter the board by assignee, due date and overdue. When they finish a task by mistake, an Undo appears for a few
  seconds. The bell tells them when someone assigns them a task and when their tasks become overdue.
- **A team leader** does the same with more rights: edits and deletes any task of the team, adds members by email,
  promotes and demotes, removes members. Removing someone unassigns their tasks. Leaders are told every morning
  about the team's overdue tasks, one message per team rather than one per task.
- **An administrator** creates users and teams in the Django admin site, sees every team, deletes teams, and finds
  teams left without a leader with a filter. Admins are not notified about every team's overdue tasks.

Users are created by administrators; there is no sign-up.

## Requirements coverage

| Requirement | Where |
|---|---|
| Task CRUD, assign, mark completed | `apps/tasks`: `/api/v1/tasks`, `.../reopen`, `.../assign-self`; the board and task dialogs |
| Filter by status and due date | `status`, `due_after`, `due_before`, plus `assignee`, `overdue`, `archived`, `team` |
| Pagination | Page number, 20 per page, `page_size` up to 100; one paginated request per board column |
| JWT authentication | SimpleJWT: 15-minute access token, rotating refresh tokens blacklisted on use and logout |
| PostgreSQL | PostgreSQL 17 in Compose; schema in each app's `models.py` |
| Tests, 80% coverage | pytest, 241 tests, 99.92% branch coverage; vitest for the frontend client |
| Docker | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` |
| API documentation | drf-spectacular: Swagger UI and OpenAPI schema; a test fails on any undocumented endpoint |
| Configuration and good practice | uv with `pyproject.toml`, ruff, mypy in strict mode, pre-commit, GitHub Actions |
| Rate limiting | 5 logins per minute per client address, 300 requests per minute per user, counted in Redis |
| Background tasks | Celery with Redis: assignment notification after the commit, daily overdue job with beat |
| React frontend, responsive | React, TypeScript (strict), Vite, TanStack Query, Tailwind; the board scrolls by column on phones |
| Seed data and demo credentials | SQL files in [`seed/`](seed/README.md), loaded by the `seed` service (psql) |
| GenAI documentation | [`GENAI.md`](GENAI.md), with the evidence in [`docs/genai-journal.md`](docs/genai-journal.md) |

## Architecture

```mermaid
flowchart LR
    browser[Browser: React app] -->|":8080"| nginx[nginx: serves the React build]
    nginx -->|"/api, /admin, /static"| api[api: Django + DRF on gunicorn]
    api --> db[(PostgreSQL)]
    api -->|"rate limit counters"| redis[(Redis)]
    api -->|"queue after commit"| redis
    redis --> worker[Celery worker]
    beat[Celery beat: daily] -->|"overdue job"| redis
    worker --> db
    migrate[migrate: one-shot migrations] --> db
    seed[seed: one-shot psql, demo SQL files] --> db
```

Inside the API, each app has the same layers. A request goes view → serializer (input shape) → service (rules and
invariants, the only code that writes) → model. Reads go through selectors. Permission rules are plain functions in
`policies.py`, called by the services, so the API, the Django admin site and the jobs all run the same rules.
Services raise domain exceptions; one handler turns them into HTTP with one JSON shape (`{code, message, details}`).

Apps depend in one direction: `core` → `accounts` → `teams` → `notifications` → `tasks`. The one exception is
documented: removing a member (`teams`) calls one `tasks` function to unassign their tasks in the same transaction.

## Data model

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : "is in"
    TEAM ||--o{ MEMBERSHIP : has
    TEAM ||--o{ TASK : owns
    USER ||--o{ TASK : "created by"
    USER |o--o{ TASK : "assigned to"
    USER ||--o{ NOTIFICATION : receives
    TEAM ||--o{ NOTIFICATION : "is about"
    TASK |o--o{ NOTIFICATION : "is about"

    USER {
        bigint id PK
        string email UK "the login, stored lowercase"
        boolean is_active "deactivated, never deleted"
        boolean is_superuser "the global administrator"
    }
    TEAM {
        bigint id PK
        string name "unique among active teams"
        int archive_after_days "default 15"
        datetime deleted_at "soft delete"
    }
    MEMBERSHIP {
        bigint team_id FK
        bigint user_id FK "unique with team_id"
        string role "leader or member"
    }
    TASK {
        bigint id PK
        bigint team_id FK
        string title
        string status "todo, in_progress, blocked, done, canceled"
        bigint created_by_id FK
        bigint assignee_id FK "optional, always a member of the team"
        date due_date "optional"
        datetime completed_at "set exactly when done or canceled"
        datetime overdue_notified_at "set by the daily job"
        datetime deleted_at "soft delete"
    }
    NOTIFICATION {
        bigint id PK
        bigint user_id FK
        bigint team_id FK
        bigint task_id FK "empty for a message about several tasks"
        string message
        datetime read_at
    }
```

Every table also has `created_at` and `updated_at`. The database itself enforces what it can: one membership per
team and user, lowercase emails, team names unique among active teams, and `completed_at` matching the status.

## Key decisions and trade-offs

The design was agreed one topic at a time before any code was written; the journal records who decided what.

- **Business rules live in services, not views or serializers.** The Django admin site would otherwise be a back
  door around them, so its forms call the same services, inlines are off and bulk delete is disabled. Cost: more
  files per app than a plain `ModelViewSet`; in return every rule is tested once, at the service.
- **Team roles in our own `Membership` table, not Django groups.** A user can lead one team and be a member of
  another; Django groups are global. The global administrator is simply `is_superuser`.
- **An assignee is always a member of the task's team.** Checked on every write, and kept true when a member
  leaves: their tasks are unassigned in the same transaction, not by a later job, so the rule is never false.
- **Done and canceled are final; only reopen leaves them** (to in progress). Simple rules over free movement.
  "Archived" is not a status but a query: finished more than `archive_after_days` (per team, default 15) ago.
- **Soft delete for teams and tasks, restored only by SQL.** Deletes are recoverable without building a restore
  feature nobody asked for. The filtering is explicit in the selectors, not hidden in a default manager.
- **Hidden things answer 404, forbidden actions 403.** A user outside a team cannot learn that its tasks exist.
- **Rate limiting.** Counted in Redis, not in process memory, because gunicorn runs several workers. The login
  limit counts per client address, which the API reads from `X-Forwarded-For` set by nginx. That header can be
  forged by any client that reaches the API directly, so the API port is not published: nginx is the only way in.
- **Notifications are polled, not pushed.** The bell asks every minute. Websockets would add a server and a
  protocol for a feature that tolerates a minute of delay. The assignment notification is queued only after the
  transaction commits; if the broker is down the change is kept and the notification is lost (logged), rather
  than failing the user's save.
- **Overdue notifications are grouped.** One message per person and team per day ("Team Y has 6 overdue tasks")
  instead of one per task, and a task is notified once. Running the job twice, or twice at the same time, sends
  nothing new.
- **Tokens in the browser.** The access token lives only in memory; the refresh token in `localStorage`, so a
  reload keeps the session. An XSS bug could read the refresh token; the damage is limited by rotation, blacklisting
  and 15-minute access tokens. An httpOnly cookie is safer but needs CSRF protection the API does not have.
- **The frontend never decides permissions.** Each task carries `can_edit` and `can_delete`, computed by the same
  policies as the API, without an extra query per task. The API still checks every action.
- **API documentation with drf-spectacular, not drf-yasg.** drf-yasg only generates OpenAPI 2 (Swagger 2.0);
  drf-spectacular generates OpenAPI 3 and serves the same Swagger UI. A test fails when an endpoint is left
  undocumented, so the documentation cannot fall behind the code.
- **Typed Python** checked by mypy in strict mode, so the layers' contracts are checked, not just documented.
- **No database index added yet.** Measured on 200k generated tasks: a member's list takes 1-5 ms without one. A
  partial index would speed up the administrator's all-teams page (90 ms to 0.3 ms) and is in the backlog until
  that page matters.

Known limits, all in the backlog: the last save wins when two people edit the same task; "Load more" pages by
number, so a task moving between columns can be skipped until the next refresh; with Redis fully down, login
fails; no change-password screen (the endpoint exists); the HTTPS settings (`check --deploy`) belong to a real
deployment behind TLS.
