# GenAI-assisted development

How this project was built with a GenAI coding tool, and how its output was checked. The raw, chronological
evidence is in `docs/genai-journal.md`; this file is the summary, filled at the end of each build phase.

Status: in progress (phase 5 done). Sections marked "pending" are filled when the phase that produces their evidence is done.

## 1. Tools and method

- Tool: Claude Code (terminal).
- Models: Claude Opus for the design conversation; Claude Fable 5.2 for the two reviews done before the build
  (journal entries 10 and 11). A different model reviewed the plan on purpose: it had no stake in the earlier
  decisions. The build session started on Claude Fable 5.2, which wrote the phase 1 scaffolding; the owner then
  switched to Claude Opus 5.5, which fixed the review findings and builds from there on (entries 12 and 13).
- Method: the design was agreed in conversation, one topic at a time, before any code. The decisions were distilled
  into `docs/implementation-prompt.md`, which was reviewed by a different model before the build and then given to
  a fresh session. Standing rules for the tool are in `CLAUDE.md`.
- Parallel build, from phase 5 (entry 24): on the owner's request, the notifications, the seed data and the
  frontend were built at the same time by three agents, each in its own git worktree and branch, with a model
  chosen per task (Claude Opus 5.5 where a subtle bug was likely, Claude Sonnet 5.5 for the mechanical seed).
  Claude Fable 5.2 wrote the briefs, agreed the API contract between the branches in advance, re-ran each
  branch's tests itself and read its diff. Each branch reaches `develop` one at a time, uncommitted, for the
  owner's review.

## 2. The prompt

The prompt was not written from memory in one sitting. It is the result of three steps, all done before any code:

1. **Planning with the AI.** The opening prompt asked for analysis only, with no code and no files (journal
   entry 1). The design was then agreed one topic at a time, with the AI asked to challenge each decision.
2. **Distilling.** Each agreed decision went into the prompt as it was taken (entry 5), so the prompt holds
   decisions, not wishes.
3. **Review by a deeper-reasoning model.** A different model (Claude Fable 5.2) reviewed the finished prompt and
   found 21 gaps, which the owner decided one by one (entry 10).

Why this way: the important decisions are taken, and the mistakes found, while changing them costs one line of
text instead of a rewrite of code. The gaps the review found would otherwise have been guessed by the model during
the build, for example auth planned after the tasks that need it, two apps that depended on each other, and admin
site paths that skipped the business rules. A precise prompt also gives more predictable code, because the model
is not left to guess.

- The implementation prompt: `docs/implementation-prompt.md`.
- The standing instructions loaded in every session: `CLAUDE.md`.
- The message that started the build session, verbatim:

  > Read CLAUDE.md, then docs/private/context.md, then docs/implementation-prompt.md.
  > Build the project phase by phase, starting at phase 1. Follow the stop rules in the plan.

## 3. Output code (representative samples)

Pending. Three samples with their commit hashes: one service that protects an invariant, one policy, and the
overdue notification job.

## 4. How the AI's suggestions were validated

Process (journal entry 11): validation is planned, not improvised. Results are pending. Per phase: the command,
its real output and the commit hash. Two review checkpoints (after the core domain and after the frontend): the
owner reads the code and an independent review runs in a fresh session.

- Phase 1 (setup): stack, health endpoint, tests, linters and hooks, entry 12. Before the first commit the owner
  walked through the scaffolding with Claude (entry 13). CI runs on `main`, which only receives merges from
  `develop` (entry 14).
- Phase 2 (accounts, auth, teams): unit, API, admin site and query-count tests, entry 16.
- Phase 3 (tasks): permission matrix, invariants, filters and query-count tests, entry 17.
- Review checkpoint 1: the owner exercised every endpoint against the running stack with an API client
  collection (one request per rule, each with its expected status) and inspected the database before moving on.
  The decisions taken during phases 2 to 4 were approved in one batch (entries 19 to 22). From then on, work
  stopped for review is left uncommitted so the owner reviews the diff before the commit (entry 23).
- Phase 4 (rate limits, API docs): limit tests and a schema test that fails on any undocumented endpoint, entry 18.
- Phase 5 (notifications): the agent's reported results were not taken on trust. The reviewing model re-ran the
  suite, then exercised the real stack: a task assigned through the services, the worker's log, the overdue
  command run twice (the second run sends nothing) and the endpoints over HTTP, entry 25.
- Phase 6 (demo seed): the suite re-run, and the seed run on the real stack twice, the second run adding nothing.
  Running it there exposed a startup-order bug the agent's isolated tests could not see, entry 28.

## 5. What was corrected or improved

Design stage (done): see journal entries 3, 6, 7, 8 and 10.

Code stage: each review finding, its fix and the commit that fixed it.

- Phase 1: nine findings in the scaffolding, found during the owner's walkthrough and fixed before the first
  commit (entry 13). The most serious: with DEBUG off, Django's default logging dropped the traceback of every
  server error; a test now runs a fresh interpreter and checks the traceback reaches stderr.
- Phase 1, found in phase 2: the type stubs described Django 6.1 while the project runs 6.0, so mypy checked the
  code against the wrong API; repinned to the 6.0 line (entry 19).
- Phase 5: the agent's code queued the assignment notification after the commit with no error handling, so a
  broker outage turned a saved change into a 500. Found by the reviewing model reading the diff, fixed with a
  test, and checked against an unreachable broker (entry 26).

## 6. Edge cases, authentication and validation

Each rule with the test that covers it. Phase 2 (entry 16):

| Rule | Covered by (`backend/apps/...`) |
|---|---|
| Email is the login, stored lowercase, case-insensitive at login | `accounts/tests/test_models.py`, `test_auth_api.py::test_login_email_is_case_insensitive` |
| Deactivated users cannot log in, and their open tokens stop working | `test_auth_api.py::test_a_deactivated_user_cannot_log_in`, `::test_a_user_deactivated_after_login_is_rejected` |
| Access tokens last 15 minutes; refresh tokens rotate and are blacklisted after use and on logout | `test_auth_api.py::test_access_tokens_last_15_minutes`, `::test_refresh_rotates_...`, `::test_logout_...` |
| Changing the password needs the current one, runs the validators, revokes older tokens | `test_auth_api.py::test_change_password_*` |
| Every error has one JSON shape; hidden resources answer 404, forbidden actions 403 | `core/tests/test_exception_handler.py`, `teams/tests/test_api.py` |
| Leaders add (by email, as member), promote, demote and remove; members can leave; teams may have no leader | `teams/tests/test_services.py`, `teams/tests/test_api.py` |
| Inactive or unknown users cannot be added | `test_services.py::test_only_existing_active_users_can_be_added` |
| Team soft delete by admins only; deleted teams are hidden and read-only; names unique among active teams | `test_services.py`, `teams/tests/test_models.py` |
| The admin site runs the services, has no bulk delete, has the orphan filter, cannot delete users | `teams/tests/test_admin.py` |

Phase 3 (entry 17):

| Rule | Covered by (`backend/apps/tasks/tests/...`) |
|---|---|
| Who may edit, reopen and delete (creator, assignee, leader, admin); ex-members have no rights | `test_services.py::test_who_may_*` (parametrized matrix), `::test_a_creator_who_left_...` |
| The assignee is an active member of the task's team | `test_services.py::test_the_assignee_must_be_...`, `::test_an_inactive_member_...` |
| Removing a member unassigns their tasks, in the same transaction | `test_services.py::test_removing_a_member_...`, `::test_member_removal_and_unassignment_...` |
| No task created finished; finished tasks read-only; reopen clears `completed_at`; the database checks `completed_at` matches the status | `test_services.py`, `test_api.py::test_finishing_then_editing_then_reopening` |
| Assign-self takes only unassigned, unfinished tasks and changes nothing else | `test_services.py::test_a_member_takes_...`, `test_api.py::test_assign_self` |
| Overdue uses today in `TIME_ZONE`; a task without a due date is never overdue | `test_selectors.py::test_is_overdue`, `::test_today_is_taken_in_the_configured_time_zone` |
| Archived is a query condition per team; reopening un-archives | `test_selectors.py::test_archived_*`, `::test_each_team_has_...`, `::test_a_reopened_task_...` |
| Hidden tasks answer 404; invalid input and filters answer 400 with field details | `test_api.py` |

Phase 4 (entry 18):

| Rule | Covered by (`backend/apps/...`) |
|---|---|
| 5 logins per minute per client address, failed attempts included; 429 with `Retry-After` | `accounts/tests/test_throttling.py::test_the_sixth_login_...`, `::test_failed_logins_count_...` |
| A forged `X-Forwarded-For` does not reset the login count | `test_throttling.py::test_a_forged_forwarded_address_...` |
| 300 requests per minute per user elsewhere; the health check is exempt | `test_throttling.py::test_the_general_limit_is_per_user`, `::test_the_health_check_...` |
| Every endpoint documents its request, responses and errors | `core/tests/test_schema.py::test_the_schema_generates_without_warnings` |
| Unknown `/api/` paths answer the JSON error shape; other paths keep the HTML page | `core/tests/test_not_found.py` |

Phase 5 (entries 25 to 27):

| Rule | Covered by (`backend/apps/...`) |
|---|---|
| Notifications are private: the list shows only the caller's, someone else's answers 404 | `notifications/tests/test_api.py`, `notifications/tests/test_services.py` |
| A deactivated user receives nothing and is never a recipient | `test_services.py::test_a_deactivated_user_...`, `tasks/tests/test_overdue_job.py::test_deactivated_users_...` |
| Overdue job: the assignee and the leaders, one message per person and team; several tasks become one team message | `test_overdue_job.py::test_one_overdue_task_...`, `::test_several_overdue_tasks_...`, `::test_tasks_are_grouped_per_team` |
| A second run sends nothing; a new due date makes the task notifiable again | `test_overdue_job.py::test_a_second_run_...`, `::test_a_new_due_date_...` |
| A task with nobody to notify stays unmarked; deleted tasks and deleted teams are ignored | `test_overdue_job.py::test_a_task_with_nobody_...`, `::test_deleted_tasks_...` |
| Assignment notifies only after the commit, never the person who assigned themselves | `tasks/tests/test_assignment_notifications.py::test_assigning_someone_else_...`, `::test_assigning_yourself_...` |
| A job that runs late sends nothing if the task was deleted or reassigned | `test_assignment_notifications.py::test_nothing_is_sent_for_a_task_deleted_or_reassigned_...` |
| A broker outage loses the notification, not the assignment | `test_assignment_notifications.py::test_a_broker_outage_...` |

Phase 6, demo seed (entries 28 and 30):

| Rule | Covered by (`backend/apps/tasks/tests/test_seed_demo.py`) |
|---|---|
| Seeded users log in with the demo-only password the command prints | `::test_creates_an_admin_and_users_...`, `::test_a_seeded_user_can_obtain_a_token` |
| The seed shows every case: each status, overdue, archived, unassigned, a leaderless team, mixed roles | `::test_every_status_...`, `::test_some_tasks_are_overdue_...`, `::test_old_finished_tasks_...`, `::test_one_team_has_no_leader_...` |
| The soft-deleted team and its tasks stay hidden | `::test_the_soft_deleted_team_...` |
| Running it twice changes nothing | `::test_running_the_seed_twice_changes_no_row_counts` |

## 7. Performance and idiomatic quality

Pending. Query-count tests on the list endpoints, one `EXPLAIN ANALYZE` of the task list query and the index
decision it led to, the output of `manage.py check --deploy`, the mypy strict result, and the ruff rule set.

- Tooling, from phase 1 (entry 12): mypy in strict mode plus `disallow_any_explicit`, with the Django and DRF
  plugins; ruff with the security (`S`), annotation (`ANN`), naive datetime (`DTZ`), Django (`DJ`) and bugbear (`B`)
  rule families; pytest fails on any warning and below 80% branch coverage. Version choices: entry 15.
- Query counts (entries 16 and 17): the team list is one query and the task list two (count and page), whatever
  the number of rows; tests fail if a change adds an N+1.
- Rate limits are counted in Redis, not in process memory: gunicorn runs several workers, and a per-process
  count would multiply every limit by the number of workers (entry 18).
- Notifications (entry 25): the list is two queries whatever the number of rows, and the overdue job reads the
  tasks and the leaders in two queries and marks the tasks with one update, instead of one query per task.
- Indexes (entry 29): `EXPLAIN ANALYZE` on 200k generated tasks. A member's list needs no index; a partial index
  would speed up the admin all-teams page, but the owner kept it for later instead of adding it before it is needed.
