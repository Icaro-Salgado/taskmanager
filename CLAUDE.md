# CLAUDE.md

A task management system: Django REST API plus React frontend, with teams, roles, task assignment and
notifications. Requirements: `docs/requirements.md`. What to build and the plan: `docs/implementation-prompt.md`.

If `docs/private/context.md` exists, read it first. `docs/private/` is git-ignored: never reference its content in
public files.

# Part 1: Development flow

## Where we are

The design is closed and was reviewed twice (journal entries 10 and 11). The work now is the build:
`docs/implementation-prompt.md`, phase by phase, starting at phase 1. Do not reopen a design decision; if the build
shows one is wrong, stop and ask the owner.

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

- `GENAI.md` at the repo root. `README.md` explains setup, connections and key decisions.
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

To be rewritten with the essential rules of the code as built (plan phase 9). Until then, the full rules are in
`docs/implementation-prompt.md`. The essentials:

- Stack: Python 3.12+, Django 6.x, DRF, SimpleJWT, drf-spectacular, PostgreSQL, Celery and Redis, React with
  TypeScript and Vite, TanStack Query, uv, ruff, mypy (strict), pre-commit, pytest, Docker Compose.
- Layering per app: `services.py` (the only write path), `selectors.py` (reads), `policies.py` (permissions),
  thin API layer. Models hold persistence and simple constraints only.
- Apps, in dependency order: `core`, `accounts`, `teams`, `notifications`, `tasks`. An app imports only from the
  ones before it; the one exception is documented in the plan.
- Global admin is `is_superuser`. Team roles (leader, member) live in `Membership`.
- An assignee must be a member of the task's team. Removing a member unassigns their tasks in the same transaction.
- Done and canceled are terminal; only reopen leaves them. "Archived" is a query condition, not a status.
- Teams and tasks are soft-deleted (`deleted_at`) and restored only by a database query.
- Security: OWASP Top 10 awareness, server-side authorization for every action, rate limiting (stricter on the
  token endpoint), input validated in serializers and invariants again in services.
