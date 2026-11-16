# CLAUDE.md

A task management system: Django REST API plus React frontend, with teams, roles, task assignment and
notifications. Requirements: `docs/requirements.md`. What to build and the plan: `docs/implementation-prompt.md`.

If `docs/private/context.md` exists, read it first. `docs/private/` is git-ignored: never reference its content in
public files.

# Part 1: Development flow

## Where we are

The design is closed and was reviewed twice (journal entries 10 and 11). The build in
`docs/implementation-prompt.md` is complete (phases 1 to 9). Work from here is fixes and backlog items the owner
asks for. Do not reopen a design decision; if one proves wrong, stop and ask the owner.

## Working agreement

- Act as a critical engineering partner: challenge questionable decisions and explain trade-offs.
- When the owner's reasoning or decision is unclear, ask. Never decide on their behalf.
- Build without waiting for approval of code. Stop only for: the open topics in the plan, a decision the plan does
  not cover, and the two review checkpoints (after phases 3 and 7).
- End of each phase: run tests and linters, report the real output, commit, add the validation entry to the
  journal, fill the matching parts of `GENAI.md`.
- Whenever you stop for the owner to review (a checkpoint, or the end of a phase you stop at), do not commit:
  run the pre-commit hooks so their fixes are in place, leave the changes in the working tree, and commit after
  the owner approves. The journal entry that needs the commit hash is written then.
- Review checkpoint: stop and tell the owner. The owner reads the core code and runs an independent review in a
  fresh session. Each finding is fixed in its own commit.
- Ideas for later go to `docs/backlog.md`; do not build them unless asked.

## Repository rules

- `GENAI.md` at the repo root. `README.md`: Part 1 is minimal (prerequisites, `run.sh` usage, links to `docs/running.md`
  and `docs/demo-data.md`); Part 2 holds the user story, design and key decisions.
- No symlinks. Check with `find . -type l -not -path './.git/*'`.
- No secrets. Seeded demo credentials are allowed but must be marked demo-only. Variables go in `.env.example`.
- Small commits with clear messages. Never commit `docs/private/`. Do not push unless the owner asks.
- Commit on `develop`. Merge into `main` (where CI runs and releases are tagged) only when the owner asks.

## Coding conventions

Typed Python: type hints on every function and method, checked by mypy in strict mode; no `Any` and no
`# type: ignore` without a reason in a comment. Small functions, no dead code, no speculative abstractions. Business rules live in
services and policies, never in views or serializers. Every rule gets a test. Tests are written alongside the code;
this is not TDD and must never be described as TDD. Coverage of at least 80% on meaningful code.

## GenAI record

Two files; each fact is written in only one of them:
- `docs/genai-journal.md` is the evidence log. Part 1 (design) is closed: do not edit or renumber it. The build
  adds entries to Part 2, using the template in that file: six lines at most, each naming the model that did the
  work, the commit and the `GENAI.md` section it feeds.
- `GENAI.md` answers the questions it must cover (its seven headings). It cites journal entries by number and does
  not repeat their text. Fill it at the end of each phase, never in one go at the end.

Rules:
- Validation entries are facts (command, real output, commit hash): log them without waiting. Never just "tests
  pass".
- Decision, correction and edge case entries are proposals: collect them and get the owner's approval in one batch
  at each review checkpoint, or at once if the build is blocked. Never document a decision silently.
- Never fabricate history. Mark entries observed or reconstructed. Quote the owner verbatim when relevant.
- Record who decided what, especially when the owner corrects Claude, and which model did the work.
- The first message of the build session goes verbatim into `GENAI.md` section 2.
- No routine edits, secrets or personal data. The session transcript is the source of truth.

# Part 2: Application rules

The code as built. The specification and its reasons: `docs/implementation-prompt.md`, `README.md` (Part 2).

## Stack and layout

Python 3.12+, Django 6.0, DRF, SimpleJWT, drf-spectacular, PostgreSQL 17, Celery and Redis (also the rate limit
cache), gunicorn; React 19, TypeScript (strict), Vite, TanStack Query, React Router, Tailwind; nginx; uv, ruff,
mypy (strict), pre-commit, pytest, vitest, Docker Compose. `backend/`, `frontend/`, `docs/`.

## Layering (backend)

- Per app: `services.py` is the only write path; `selectors.py` reads; `policies.py` holds permission rules as
  pure functions (no errors raised); serializers validate input shape; views are thin and call services and
  selectors. Models hold persistence and simple constraints only. No business rule in a view or serializer.
- Services raise the domain errors in `apps/core/exceptions.py` and import nothing from DRF;
  `apps/core/exception_handler.py` maps them to HTTP. Every error is `{code, message, details}`. A resource the
  user cannot see answers 404; one they can see but may not change answers 403.
- Apps in dependency order: `core`, `accounts`, `teams`, `notifications`, `tasks`; each imports only from earlier
  ones. One exception: `teams.services.remove_member` calls `tasks.services.unassign_member_tasks` in the same
  transaction (an explicit call, not a signal). `notifications` only stores and delivers; who is notified about
  what is decided in `tasks`.
- The Django admin site runs the same services: no inlines, `delete_selected` disabled, tasks read-only, users
  never deleted.

## Domain rules

- Users: email login, stored lowercase; deactivated, never deleted. Global admin is `is_superuser`. No sign-up.
- Teams: name unique (ignoring case) among active teams, max 30; `archive_after_days` default 15. A team may have
  no leader. Roles (`leader`, `member`) live in `Membership`, unique per (team, user).
- Tasks: statuses `todo`, `in_progress`, `blocked`, `done`, `canceled`. Done and canceled are terminal and
  read-only; only reopen leaves them (to `in_progress`, clearing `completed_at`). A task cannot be created
  finished. "Archived" is a query (finished more than `archive_after_days` ago), never a status. Overdue: due
  before today in `TIME_ZONE` and not finished.
- An assignee is an active member of the task's team, checked on every write that sets it. Removing a member
  (or leaving) unassigns their tasks in the same transaction.
- Permissions: only current members (and admins) have rights on a team's tasks. Create: any member. Edit and
  reopen: creator, assignee, leader, admin. Delete: creator, leader, admin. Assign-self: members only, unassigned
  unfinished tasks. Manage members: leaders and admins; anyone may leave. Delete a team: admins.
- Soft delete for teams and tasks (`deleted_at`, `deleted_by`); selectors exclude them explicitly (no custom
  default manager). Restored only by SQL (`docs/demo-data.md`).
- Notifications: an assignment by someone else is queued with `transaction.on_commit`; a broker failure is logged
  and the change is kept. The daily overdue job notifies the assignee and the team's leaders, grouped per person
  and team, marks `overdue_notified_at`, and skips locked rows, so a rerun sends nothing new.

## API and security

- Under `/api/v1`. Tasks are paginated (20, max 100) and ordered by due date (empty last), then id. The task
  payload carries `can_edit` and `can_delete` from the policies; the frontend never decides permissions itself.
- JWT: 15-minute access token; refresh tokens rotate and are blacklisted on use, on logout and on password change.
- Rate limits in Redis: login 5/min per client address, 300/min per user elsewhere. The api is reached only
  through nginx (`DRF_NUM_PROXIES=1`); never publish the api port, or `X-Forwarded-For` can be forged.
- Every endpoint is documented in the OpenAPI schema; a test fails on any schema warning.

## Frontend

All HTTP goes through `frontend/src/api/client.ts` (one shared token refresh, `ApiError` with the API's error
shape). Access token in memory, refresh token in `localStorage`. Server data lives in TanStack Query; after a
change, the task lists are invalidated. Features in `src/features/<area>/`, each with its `queries.ts`.

## Run and test

- `./run.sh` (up, down, test; `run.ps1` is untested) starts the stack and seeds it (`up --no-seed` skips it); app, API, Swagger and admin
  on http://localhost:8080. Demo data: SQL files in `backend/seed/`,
  loaded with psql by the one-shot compose `seed` service; credentials in `docs/demo-data.md`.
- Backend: `./run.sh test`, or in `backend/` with `.env` loaded: `uv run pytest`, `ruff check`, `mypy .`.
  Coverage must stay at or above 80%. Query-count tests guard the list endpoints against N+1.
- Frontend, in `frontend/`: `npm run lint`, `npm test`, `npm run build`.
- Tests run with throttling off (rate limit tests opt back in) and Celery eager.
