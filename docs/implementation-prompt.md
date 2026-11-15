# Implementation prompt

Follow `CLAUDE.md` for rules and working method. This file describes what to build and the plan to build it.
Requirements: `docs/requirements.md`.

## Goal

A task management system: Django REST API plus React frontend, with teams, roles, task assignment and overdue
notifications.

The work is finished when all of this is true:
- From a fresh clone, one command starts the whole stack (db, redis, api, worker, beat, frontend), applies
  migrations and loads the seed data: `./run.sh` (Linux, macOS, WSL) or `.\run.ps1` (Windows, written but not
  tested).
- The seeded demo users (credentials marked demo-only) can log in through the React app.
- Every feature below works end to end: API, Django admin site, notifications, frontend.
- Tests pass with coverage of at least 80% on meaningful code. `ruff`, `mypy` and `pre-commit` are clean.
- Swagger/OpenAPI docs are served. The browser console shows no warnings (the owner checks it by hand).
- `README.md` and `GENAI.md` are complete. No symlinks, no secrets in the repo.
- The git history shows the work in small, meaningful commits, one or more per phase.

## Stack

Python 3.12+, Django 6.x, DRF, SimpleJWT, drf-spectacular, PostgreSQL, Celery with Redis (Redis also backs rate
limiting), React with TypeScript and Vite, TanStack Query, uv, ruff, pre-commit, pytest with pytest-django and
pytest-cov, gunicorn, nginx, Docker and docker-compose, GitHub Actions. `USE_TZ = True`; `TIME_ZONE` comes from the
environment (default `America/Sao_Paulo`) and Celery uses the same value.

Typed Python: every function and method in the backend has type hints, tests included. mypy checks it in strict
mode with `django-stubs` and `djangorestframework-stubs`, in pre-commit and in CI. No `Any` and no
`# type: ignore` without a comment giving the reason. The frontend uses TypeScript in strict mode.

Repo layout: `backend/`, `frontend/`, `docs/`, with `docker-compose.yml`, `run.sh`, `run.ps1`, `README.md`,
`GENAI.md`, `.env.example` and `.gitattributes` at the root, plus `.github/workflows/ci.yml` (ruff, mypy and pytest
with coverage on pushes to `main`; changes to docs only are skipped).

## Models

Every model has `created_at` and `updated_at` (an abstract base model).

- **User**: custom model, email is the login, stored lowercase. Users are deactivated (`is_active = False`), never
  deleted. `is_superuser` is the global admin; `is_staff` only allows Django admin login.
- **Team**: `name` (max 30, unique among teams that are not deleted), `archive_after_days` (positive integer,
  default 15), `deleted_at`, `deleted_by` (soft delete).
- **Membership**: team, user, role (`leader` or `member`), unique on (team, user).
- **Task**: team, title, description, status, created_by (`PROTECT`), assignee (nullable, `SET_NULL`), due_date
  (nullable `DateField`), completed_at, overdue_notified_at, `deleted_at`, `deleted_by` (soft delete).
  Statuses: `todo`, `in_progress`, `blocked`, `done`, `canceled`.
- **Notification**: user, team, task (nullable), message, created_at, read_at.

## Rules

Soft delete (restorable deletes):
- Deleting a team or a task never removes the row: the service sets `deleted_at` and `deleted_by`. Memberships and
  tasks of a deleted team are left untouched.
- Selectors exclude deleted teams, deleted tasks and tasks of deleted teams. No custom default manager: the
  filtering is explicit in the selectors.
- Restoring is done only with a database query (no UI, no endpoint), for example
  `UPDATE teams_team SET deleted_at = NULL, deleted_by_id = NULL WHERE id = ...;`. `README.md` documents it.
  Restoring a team fails if an active team has taken its name meanwhile.
- Only admins delete teams. Membership removal is a real delete (see below).

Teams and members:
- Only admins create teams (Django admin site).
- A team can have several leaders. A user can belong to and lead several teams.
- Leaders add members by exact email; a new member always gets the `member` role. No endpoint lists all users.
- Every member of a team can see its member list, leaders included, with each role.
- Leaders can promote a member to leader, and remove or demote any member of their team, including other leaders
  and themselves. Any member can leave a team. A team with no leader is allowed; admins find such teams with an
  "orphan teams" filter in the Django admin site.
- Removing a member unassigns their tasks in that team, in the same transaction.
- A user who is no longer a member has no rights on that team's tasks, even ones they created.
- A deactivated user keeps their memberships and assigned tasks, so reactivating restores everything. While
  inactive they cannot log in, receive no notifications, and cannot be added to a team or picked as a new assignee.
  The Django admin site cannot delete users.

Tasks:
- Any member of a team can create a task in it; an admin can create one in any team.
- An assignee must be a member of the task's team (service-layer invariant, tested).
- The team of a task cannot change after creation.
- Who may edit a task: its creator, its assignee, a leader of its team, an admin. They can change any field,
  including the assignee (to any team member).
- Any team member can assign themselves to an unassigned task, through a dedicated action:
  `POST /api/v1/tasks/{id}/assign-self`. It changes nothing else.
- Who may delete a task: its creator, a leader of its team, an admin.
- All members of a team can see its tasks.
- A task cannot be created in a terminal status (`done`, `canceled`). Non-terminal statuses move freely.
- Entering a terminal status sets `completed_at`. Terminal tasks are read-only except for reopen and delete.
- Reopen: `POST /api/v1/tasks/{id}/reopen` moves a terminal task to `in_progress` and clears `completed_at`.
  Allowed for whoever may edit the task. No server-side time window.
- "Archived" is not a status. It is a query condition: a terminal task whose `completed_at` is older than the
  team's `archive_after_days`. No job, no column, no status. The task list excludes these tasks by default; the
  `archived` filter returns them instead. A reopened task no longer matches, because `completed_at` is cleared.
- Overdue means `due_date` is before today (in `TIME_ZONE`) and the task is not terminal. The API returns
  `is_overdue`; the frontend never computes it. Changing `due_date` or reopening clears `overdue_notified_at`.

Admin:
- Admins can do everything, through the API and the Django admin site.
- In the Django admin site, membership changes and team deletes call the services (`save_model`, `delete_model`),
  so the rules above always run. Nothing may skip them: no inlines, and the "delete selected" bulk action is
  disabled for teams and for memberships. Tasks are read-only there.

## Layering

Per Django app: `services.py` (the only write path), `selectors.py` (read queries), `policies.py` (permission
rules), and a thin API layer (serializers and views). Models hold persistence and simple constraints only.
No repository wrapper.

Apps and dependency direction: `core` (base model, domain exceptions), `accounts`, `teams`, `notifications`,
`tasks`. Each app imports only from the ones before it in that list.
- `notifications` only stores and delivers: it offers a service to create a notification and knows no task rule.
  Its `task` foreign key is declared by name (`"tasks.Task"`), without importing the tasks app. Who is notified
  about what is decided by the app that owns the rule, so the overdue job and the assignment notification live in
  `tasks`.
- One documented exception: removing a member (in `teams`) calls a single `tasks` service function that unassigns
  that member's tasks, inside the same transaction. An explicit call was chosen over a signal because it is
  easier to read and to test.

## Errors

Services and policies raise domain exceptions and import nothing from DRF. One DRF exception handler maps them to
HTTP, so every error has the same JSON shape. A resource in a team the user cannot see answers 404 (its existence
is not revealed); a resource the user can see but may not change answers 403.

## API

Under `/api/v1`: token and refresh (SimpleJWT), logout (blacklists the refresh token), current user, change
password, teams and members (list, add, change role, remove or leave), tasks (CRUD, reopen, assign-self, filters:
team, status, due date range, assignee, overdue, archived; pagination with a maximum page size), notifications
(list, mark read), health. Schema and Swagger from
drf-spectacular. Task lists are ordered by `due_date`, soonest first and empty dates last, then by `id`.

## Security

- Access tokens last 15 minutes. Refresh tokens rotate and are blacklisted after rotation and on logout.
- Changing the password requires the current password, runs Django's password validators, and invalidates tokens
  issued before it (SimpleJWT `CHECK_REVOKE_TOKEN`). Phase 1 confirms the pinned SimpleJWT version supports this;
  if it does not, stop and ask the owner.
- Rate limiting backed by Redis: 5 requests per minute per client on the token (login) endpoint, 300 per minute
  per user elsewhere (both set in the environment). nginx forwards the client address and DRF `NUM_PROXIES` is
  set, so the login limit counts real clients, not the proxy. Tests run with throttling off, except the tests that
  check the limits.
- Authorization on the server for every action. Input validated in serializers; invariants again in services.
- No secrets in the repo; `.env.example` documents every variable.

## Notifications

A Celery beat job runs daily, at a time set in the environment (default 08:00 in `TIME_ZONE`). It selects overdue
tasks not yet notified (`overdue_notified_at` is null), ignoring deleted tasks and tasks of deleted teams, and for
each recipient (the assignee, and every leader of the team) groups them per team:
- one task: a notification about that task ("Task X is overdue"),
- more than one: a single notification for the team ("Team Y has N overdue tasks").
Admins receive no overdue notifications (unless they are the assignee or a leader of the team).
It then sets `overdue_notified_at` on the tasks that had at least one recipient, in one transaction, so running the
job again sends nothing new. A task with nobody to notify (no assignee, no leader) stays unmarked and is picked up
once someone exists.
A management command runs the same job on demand for demos.

Assignment: when a task is assigned to someone other than the user making the change, a Celery task, queued with
`transaction.on_commit`, creates a notification for the new assignee ("You were assigned task X"). If the task is already
overdue, the message says so; a task the job already notified is not notified again. Assigning yourself sends
nothing.

The frontend reads notifications by polling every 60 seconds; there are no websockets.

## Frontend

Login, team selector (an admin sees all teams), task board with filters (see below), create and edit dialog, task
detail with the reopen action, an undo toast for a few seconds after a task becomes terminal (calls reopen), a
notification bell, and a teams page where leaders manage members. Responsive, no console warnings (the
owner checks the console by hand; an automated check is in the backlog). No admin screens.

Task board: one column per status. Each column is its own paginated request (status filter, "load more"), in the
API's default order. The other filters (assignee, due date range, overdue) apply to every column. A task changes
status through a control on its card; drag and drop is in the backlog. Archived tasks are shown as a plain
paginated list, not on the board.

Token refresh: only one refresh request runs at a time and the other failed requests wait for it, because the
refresh token rotates and a second parallel refresh would log the user out.

The `frontend` container is a production build served by nginx, which also proxies `/api`, the Django admin site
and Swagger to the api container: one origin, no CORS. The api runs under gunicorn and serves its own static files
with WhiteNoise.

## Running everything

Docker Compose holds all the logic, so it works the same on every OS: a one-shot `migrate` service applies
migrations and loads the seed data (safe to run twice) before api, worker and beat start. PostgreSQL is published
on the host (port from `.env`, default 5432) so a database client can connect.
Two thin wrappers at the repo root, with the same commands:
- `run.sh` (Linux, macOS, WSL) and `run.ps1` (Windows PowerShell).
- `up` (default): create `.env` from `.env.example` if missing, then `docker compose up --build -d`, then print
  the URLs (app, API, Swagger, Django admin) and where the demo credentials are documented.
- `down`: `docker compose down`.
- `test`: run the backend tests with coverage inside the api container.
`.gitattributes` forces LF line endings for `*.sh` and `run.sh` is committed as executable.
`run.ps1` is written but not tested on Windows; the README says which platforms were actually verified.

## README

`README.md` has two parts.

1. **Setup and instructions**: what the project does, prerequisites, how to run (`run.sh`, `run.ps1` and plain
   `docker compose`), URLs, demo credentials (marked demo-only), how to connect to PostgreSQL from a client such as
   DBeaver (host, port, database, user, password from `.env`), how to restore a soft-deleted team or task with SQL,
   how to run the tests and the overdue job on demand, and the project structure.
2. **User story**: who uses the system and what they do with it (admin, leader, member), then the thought process
   behind it: the key decisions with their trade-offs, and an architecture diagram.

## Git

- Phase 1 starts with `git init` (branch `main`).
- Branches: all work is committed on `develop`. `main` only receives merges from `develop`, when the owner asks,
  and releases are tagged on `main`. CI runs on pushes to `main`.
- Then extend the existing root `.gitignore`: keep every entry already there (`docs/SESSION_HANDOFF.md`,
  `docs/private/`) and add the usual ignores for Python (`__pycache__/`, `.venv/`, `.pytest_cache/`,
  `.ruff_cache/`, coverage files), Node (`node_modules/`, `dist/`), environment files (`.env`, but not
  `.env.example`), and editor and OS files.
- Before the first commit, confirm with `git status` and `git check-ignore` that `docs/private/` and `.env` are
  ignored.
- First commit: the scaffolding. Second commit: the initial tests. Then commit at least once per phase, only when
  its tests and linters pass. Small commits with clear messages. Do not push; the owner adds the remote.

## Plan

Work phase by phase. Write tests alongside the code. At the end of each phase, run the tests and linters, report
the real output, commit, log the validation entry in the journal (command, real output, commit hash) and fill the
matching parts of `GENAI.md`. Keep going without waiting for approval of code. Stop only for: the two review
checkpoints below, the open topics, or a decision this file does not cover. Journal entries that record a decision
or a correction are kept as proposals and approved by the owner in one batch at each checkpoint.

Review checkpoints (after phase 3 and after phase 7): stop and tell the owner. The owner reads the core code
(services and policies after phase 3, the frontend after phase 7) and runs an independent code review in a fresh
session. Each finding is fixed in its own commit, and the finding, the fix and the commit hash go to the journal.

1. **Setup.** `git init` and the `.gitignore` update (see Git). Pin versions and confirm DRF, SimpleJWT,
   drf-spectacular and Celery support Django 6.x, that SimpleJWT supports `CHECK_REVOKE_TOKEN`, and that
   `django-stubs` supports the pinned Django (if it does not, stop and ask the owner).
   Done when: `run.sh` starts db, redis and api, and `run.ps1` mirrors it (not tested); the health endpoint
   answers; pytest runs with coverage; `ruff`, `mypy` and `pre-commit` pass; the CI workflow exists; settings come from
   environment variables; the scaffolding and the initial tests are committed separately.
2. **Accounts, auth and teams.** Done when: User, Team and Membership exist with the base timestamps, services,
   policies and selectors; token, refresh, logout, current user and change password work; the team and member
   endpoints work; domain errors reach the client through the single exception handler; team soft delete works;
   the Django admin site manages them through the services, with the orphan teams filter; their rules are tested,
   including unauthenticated and forbidden access.
3. **Tasks.** Done when: every task rule above works through the API and is tested, including the permission
   matrix, the assignee invariant, terminal rules, reopen, assign-self, soft delete, archived and overdue; list
   endpoints avoid N+1 queries, proven by query-count tests.
   **Review checkpoint.**
4. **Throttling and docs.** Done when: rate limits are in place and tested; Swagger is served.
5. **Notifications.** Done when: the worker and beat run in compose; the overdue job sends one notification for a
   single task and one team notification for several; running it twice sends nothing new; the management command
   runs it on demand; assigning a task to someone else notifies them after the commit; the notification endpoints
   work.
6. **Seed data.** Done when: the seed creates demo users, an admin, teams (including one without a leader and one
   soft-deleted), memberships and tasks in every status, including overdue tasks and finished tasks old enough to
   match the archived filter, with credentials marked demo-only, and the `migrate` service loads it. One
   `EXPLAIN ANALYZE` of the task list query, run on enough generated rows to be meaningful (not committed as seed),
   is recorded in the journal and settles the index question.
7. **Frontend.** Done when: the seeded users can do everything in the Frontend section against the real API, the
   app is responsive and the console is clean (the owner checks the console at the checkpoint).
   **Review checkpoint.**
8. **Finish.** Done when: `run.sh` works from a fresh clone; coverage is at least 80%; `README.md` matches the
   README section; `GENAI.md` is complete, with three code samples and their commit hashes (one service that
   protects an invariant, one policy, the overdue job); the output of `manage.py check --deploy` is recorded;
   `find . -type l -not -path './.git/*'` prints nothing; no secrets are committed.
9. **Update `CLAUDE.md`.** Rewrite its "Application rules" part so it holds the essential rules of the code as
   built (models, invariants, permissions, layering, how to run and test), short enough to load in every session.
   Show the diff to the owner before committing.

## Open topics (ask the owner when their phase is reached)

Frontend token storage, styling approach, database indexes (only when a real query justifies them).
Ideas for later: `docs/backlog.md`.
