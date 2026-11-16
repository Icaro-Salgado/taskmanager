# Building with a GenAI tool

I built this project with Claude Code. The AI wrote most of the code. I decided what to build, wrote the rules
it had to follow, and checked what it produced.

This page answers seven questions, one per numbered section: the tools, the prompt, the code it produced, how I
validated it, what was corrected, how edge cases and authentication were handled, and how I judged performance
and style. The raw log, with real command output and commit hashes, is
[`docs/genai-journal.md`](docs/genai-journal.md). A number in brackets such as (entry 26) points to an entry
there. Quotes are verbatim, typos included.

## In short

- **The prompt came last, not first.** I agreed the design with the AI one topic at a time. Each decision went
  into [`docs/implementation-prompt.md`](docs/implementation-prompt.md) as it was taken. A second model then
  reviewed that prompt before any code existed and found 21 gaps (section 2).
- **I corrected the model, and it corrected me.** I stopped it when it rushed, when it turned my questions into
  features, and when it kept code I had asked it to remove. It showed me that one of my own rules made a field
  meaningless, and that the CI trigger I asked for would never fire (section 5).
- **A report from the AI is a claim, not a result.** Every phase ends with the command, its real output and the
  commit. Three times, running the work again found what the reports had missed (section 4).
- **The checks found real defects in generated code.** A forged header escaped the login rate limit. A broker
  outage turned a saved change into a 500. Two browser tabs logged each other out (section 5).
- **Where it stands:** 244 backend tests at 99.92% branch coverage, mypy (strict) and ruff clean. Section 4 also
  lists what was not checked.

## 1. Tools and method

The tool is Claude Code, in the terminal.

| Stage | Model | Notes |
|---|---|---|
| Design conversation | Claude Opus | One topic per step (entries 1 to 9) |
| Two reviews before the build | Claude Fable 5.2 | A different model from the one that helped design it (entries 10 and 11) |
| Build | Claude Fable 5.2 for the phase 1 scaffolding, then Claude Opus 5.5; Claude Sonnet 5.5 for the demo data | Each journal entry names the model that did the work (entries 12, 13 and 28) |
| Review after the build | Claude Fable 5.2, in a fresh session | It had none of the build's context (entry 39) |

The method has three parts. The design is agreed in conversation before any code. The decisions become a prompt
that a fresh session builds from, phase by phase. The standing rules for the tool are in [`CLAUDE.md`](CLAUDE.md),
loaded in every session.

The build has nine phases (section 2). From phase 5 it ran in parallel (entry 24). I asked for it in these words: "subagents with the proper
model (for token optimization without loose quality or create bugs), if it is parelizable, each works on a
different branch". Three agents built the notifications, the demo data and the frontend, each in its own git
worktree and branch. Claude Fable 5.2 wrote their briefs and fixed the API contract between the branches in
advance. It then re-ran each branch's tests itself and read each diff. Each branch came to `develop` one at a
time, uncommitted, for my review.

## 2. The prompt

The prompt was not written in one sitting. It is the result of three steps, all done before any code:

1. **Planning.** My opening prompt asked for analysis only: no code, no files, and the AI in the role of a
   critical engineering partner (entry 1). When it answered with a data model, endpoints and six questions in
   one message, I slowed it down: "you are rushing it [...] lets start with the journal and claude instructions,
   so we start discussing the arch and project per part" (entry 3). From then on, one topic per step.
2. **Distilling.** Each agreed decision went into the prompt when it was taken (entry 5). The prompt holds
   decisions, not wishes.
3. **Review by another model.** I asked a different model to "see if there is any flaws or if its ok"
   (entry 10). It found no flaw in the foundation and 21 gaps. I decided each one.

Why this way: a model fills every gap in a prompt with a guess, and the guesses look reasonable. Deciding first
means a mistake costs one line of text and not a rewrite. Three of the gaps the review found show what the
model would have guessed during the build: auth was planned after the tasks that need it, the boundaries
between the apps were undefined, and paths in the admin site skipped the business rules.

One limit: this is not a one-shot prompt. It is the distilled end of a long conversation, and it worked
because of that conversation.

What makes the prompt usable by a model:

- **The goal is a list of conditions** that are true when the work is finished, not a description of the work.
- **Phases 1 to 8 each have a "Done when" test** the model can check itself against. Phase 9 only updates
  `CLAUDE.md`.
- **It names the only cases where the model must stop and ask**: two review checkpoints, the open topics, and
  any decision the prompt does not cover. Everything else it builds without waiting.

One phase, verbatim:

> 3. **Tasks.** Done when: every task rule above works through the API and is tested, including the permission
> matrix, the assignee invariant, terminal rules, reopen, assign-self, soft delete, archived and overdue; list
> endpoints avoid N+1 queries, proven by query-count tests. **Review checkpoint.**

The message that started the build session, verbatim:

> Read CLAUDE.md, then docs/private/context.md, then docs/implementation-prompt.md.
> Build the project phase by phase, starting at phase 1. Follow the stop rules in the plan.

(`docs/private/context.md` is a file of personal notes that is kept out of the repository.)

The full prompt is [`docs/implementation-prompt.md`](docs/implementation-prompt.md).

## 3. Output code (representative samples)

Three excerpts of the generated code, written by Claude Opus 5.5 from the implementation prompt. Each one
carries a rule.

### A service that protects an invariant

`backend/apps/tasks/services.py` and `backend/apps/teams/services.py` (first written in commit `4ecec2a`; the
row lock was added after the last review, see section 5).

What to look at:

- The rule "an assignee is an active member of the task's team" is checked whenever a task is created or
  reassigned.
- It is kept true from the other side too: removing a member unassigns their tasks in the same transaction.
- The service raises a domain error and knows nothing about HTTP. One handler maps it to a response.
- `teams` calls `tasks` explicitly. It is the one documented exception to the app order, and I chose it over a
  signal (entry 10).
- Both functions lock the same membership row, so an assignment and a removal at the same time cannot slip
  past each other.

```python
def _assignee_for(team: Team, user_id: int | None) -> User | None:
    """The invariant: an assignee is an active member of the task's team.

    The membership row is locked until the caller's transaction ends, so a removal running at the
    same time waits and then unassigns the task: no non-member is ever left assigned.
    """
    if user_id is None:
        return None
    membership = (
        Membership.objects.select_for_update(of=("self",))
        .select_related("user")
        .filter(team=team, user_id=user_id, user__is_active=True)
        .first()
    )
    if membership is None:
        raise RuleViolationError(
            "The assignee must be an active member of the team.", code="invalid_assignee"
        )
    return membership.user


def remove_member(*, actor: User, membership: Membership) -> None:
    """Removes a member, or lets a member leave. A team may end up with no leader.

    Their tasks in this team are unassigned in the same transaction, so an assignee is always a
    member. The membership row is locked first (see `tasks.services._assignee_for`). This is the
    one call from `teams` into `tasks` (an explicit call, not a signal).
    """
    _ensure_active(membership.team)
    if not policies.can_remove_member(actor, membership.team, membership.user):
        raise PermissionDeniedError("Only team leaders can remove other members.")
    with transaction.atomic():
        # Locked first: an assignment to this member running at the same time either finishes
        # before the unassignment below, or waits and then finds no membership.
        if not list(Membership.objects.select_for_update().filter(pk=membership.pk)):
            raise NotFoundError("Membership not found.")
        unassign_member_tasks(team=membership.team, user=membership.user)
        membership.delete()
```

### A policy

`backend/apps/tasks/policies.py` (commit `0e09fc6`).

What to look at:

- A permission is a function that returns yes or no. It raises nothing, so the same rule answers the API's
  check and the `can_edit` flag the frontend reads.
- `role is None` comes first: an ex-member who created the task, or was assigned to it, has no rights.
- The `_with_role` variant is pure. It takes the role the list query already annotates, so a page of tasks costs
  no extra query per task (`test_list_queries_do_not_grow_with_the_number_of_tasks`). The plain variant does one
  membership lookup.

```python
def can_edit_task(user: User, task: Task) -> bool:
    """Creator, assignee, team leader or admin. Also governs reopen."""
    return can_edit_task_with_role(user, task, role_in(task.team, user))


def can_edit_task_with_role(user: User, task: Task, role: Role | None) -> bool:
    if is_admin(user):
        return True
    if role is None:
        return False
    return role == Role.LEADER or user.pk in (task.created_by_id, task.assignee_id)
```

### The overdue job

`backend/apps/tasks/services.py` (commit `80a727c`).

What to look at:

- Two reads, one insert per person and team, and one update, whatever the number of tasks.
- One message per person and team: one task by name, several as a count.
- Only tasks that reached someone are marked. A task with nobody to tell is picked up later.
- `SKIP LOCKED` keeps two runs at the same moment from telling anyone twice (entries 25 and 27).
- The Celery task and the management command are thin wrappers around this one function.

```python
def notify_overdue_tasks() -> OverdueRun:
    """The daily job: one notification per recipient and team, then the tasks are marked.

    Marked tasks are never picked again, so a second run sends nothing new. A task with nobody to
    notify stays unmarked and is picked up once it has an assignee or a leader.
    """
    with transaction.atomic():
        # Rows locked by a run in progress (beat and the command at once) are skipped, so no task
        # is notified twice.
        tasks = list(
            selectors.overdue_tasks_to_notify(timezone.localdate()).select_for_update(
                skip_locked=True, of=("self",)
            )
        )
        leaders = selectors.active_leaders_by_team({task.team_id for task in tasks})
        groups: dict[tuple[User, Team], list[Task]] = defaultdict(list)
        for task in tasks:
            for user in _overdue_recipients(task, leaders.get(task.team_id, [])):
                groups[(user, task.team)].append(task)
        for (user, team), user_tasks in groups.items():
            message, task_id = _overdue_message(team, user_tasks)
            create_notification(user=user, team=team, message=message, task_id=task_id)
        notified = {task.pk for user_tasks in groups.values() for task in user_tasks}
        Task.objects.filter(pk__in=notified).update(overdue_notified_at=timezone.now())
    return OverdueRun(notifications=len(groups), tasks=len(notified))
```

## 4. How the AI's suggestions were validated

The rule: "tests pass" is not a result. Each phase ends with the command, its real output and the commit hash,
written in the journal. The build stopped twice for my review, after the core domain and after the frontend.
After the build, a fresh session with none of the build's context reviewed the whole repository (entry 39).

This rule did not exist at first. Before the build I asked the reviewing model about the process itself: "I'm
not sure we are being efficient here". Its finding: my plan covered the prompt and produced no evidence about
the generated code. The checkpoints and the evidence rule come from that review (entry 11).

Three times, running the work again found what the reports had missed:

- **The demo seed** came back from its agent with its tests passing. On the real stack it failed at startup,
  because the service that loaded it did not wait for Redis (entry 28). That seed code was later replaced by
  plain SQL files (entry 41).
- **Three rate limit tests** failed in the container only, after the merge: there the API trusted one proxy,
  and the tests assumed none (entry 32).
- **The CI workflow** had never run, so nothing had ever tested it. A fresh session ran the tests with exactly
  the variables the workflow sets: `15 failed, 234 passed` (entry 39).

What was checked at each step:

| Step | Checked how | Entry |
|---|---|---|
| Phase 1, setup | Stack, health endpoint, tests, linters, hooks. Before the first commit, Claude walked me through the scaffolding: nine findings | 12, 13 |
| Phase 2, accounts, auth, teams | Unit, API, admin site and query-count tests; a login with curl on the running stack | 16 |
| Phase 3, tasks | Permission matrix, invariants, filters, query counts; a create, finish, reopen flow with curl | 17 |
| Review checkpoint 1 | My review of the core code. The decisions taken during phases 2 to 4 were approved in one batch | 19 to 22 |
| Phase 4, rate limits, API docs | Six failed logins with curl: `401 401 401 401 401 429`. A test that fails on any undocumented endpoint | 18 |
| Phase 5, notifications | The reviewing model re-ran the suite, then assigned a task on the real stack, read the worker's log, and ran the overdue command twice | 25 |
| Phase 6, demo data | The suite re-run; the seed loaded twice on the real stack, the second load adding nothing | 28, 42 |
| Phase 7, frontend, checkpoint 2 | Every check re-run after the merge; the stack exercised through nginx with curl. Then Claude walked me through the frontend file by file | 31, 34 |
| After the build | A fresh session reviewed the whole repository and probed the running API with malformed input | 39 |

From checkpoint 1 on, work stopped for my review is left uncommitted. I asked for it because a diff is easier to
review than a commit (entry 23).

### What was not checked

- **Requests in parallel, inside the test suite.** The two races found by the last review are fixed (section
  5) and were tried on the running stack with two requests sent at the same time. The suite itself checks the
  lock and the out-of-date read; it has no test that runs two requests in parallel.
- **Redis fully down.** Only a broker outage was tried. Rate limiting counts in the same Redis, so with Redis
  fully down login answers 500 (entry 26).
- **The browser console, inside the test suite.** It was checked with a headless browser on the login, board,
  task dialog, archived and members pages: no messages. That check is not a test yet (backlog).
- **`run.ps1`** was written and never run on Windows. My instruction was "dont test just do it" (entry 10).
- **The `EXPLAIN ANALYZE` plans** were read in a session and not saved. Only the numbers are in the journal
  (entry 29).
- **One journal entry is reconstructed**, not observed: my exact words were not kept (entry 36).
- **Every reviewer was a model.** The independent reviews used a different model or a fresh session, never a
  second human.

## 5. What was corrected or improved

### Where I corrected the model

- **Scope.** The model read my "what if" questions as features to build. I was testing whether the base design
  would survive future needs. The rule since then: if a question does not change the foundation, it goes to the
  backlog (entry 6). Later I noticed the design drifting into "an internal tool for companies", which the
  requirements do not ask for. The model agreed and recommended starting the build (entry 7).
- **Demo data in the code.** I asked for the sample data to leave the code: "the sample data is too hardcoded on
  the code". The model moved it to SQL files but kept a `seed_demo` command, and then kept its tests. My answer:
  "CODE SHOULD NOT KNOW ABOUT DEMO DATA". Both were deleted (entry 41).
- **Archived tasks.** In my last review of the prompt I added a rule the model had not proposed: "archived is
  not a status but a query result". No job, no column, nothing to get out of sync (entry 9).

### Where the model corrected me

- **Free movement between statuses.** I chose it. The model pointed out that `completed_at` then has no clear
  meaning when a finished task moves again. I reversed my decision: "Lets make the simples rules". Done and
  canceled became final, with one explicit reopen action (the "Design decisions" table in the journal).
- **Unassigning in a background job.** I asked whether removing a member could unassign their tasks later, in a
  job. The model's answer: the rule "an assignee is a member" must never be false, so it happens in the same
  transaction (same table in the journal).
- **CI on pull requests.** I asked for it: "every push is a waste of actions". The model pointed out that we
  commit straight to a branch, with no pull requests, so CI would never run. I then decided: work on
  `develop`, CI on pushes to `main` (entry 14).
- **Hiding which emails have accounts.** I wanted the add-member endpoint to always answer ok, "so the user
  cant find which members we have". The model showed that this alone hides nothing, because the new member
  appears in the list at once; only an invitation flow hides it. I chose that design and put it in the backlog
  (entry 21). The README lists the leak under its security decisions.
- **Its own design.** The assignment notification the model proposed created a second circular dependency
  between two apps. It found this itself in the review, and `notifications` became a delivery-only app (entry 10).

### Defects found in generated code

Most serious first.

| Defect | How it was found | Fix | Entry, commit |
|---|---|---|---|
| A forged `X-Forwarded-For` header escaped the login limit: seven tries, seven `401`, no `429` | The reviewing model noticed the API port was still published while the API trusted one proxy. Then it was measured | The API port is no longer published; nginx is the only way in | 33, `5dae757` |
| With the broker down, a change that was already saved answered 500 | Reading the agent's diff: the notification was queued with no error handling | Catch, log, keep the change. Checked against an unreachable broker | 26, `124babf` |
| Two tabs renewing their token at once logged each other out | Walking through the frontend file by file with me | The refused tab retries with the token the other tab stored. A test fails without the fix | 34, `e107c41` |
| The CI workflow would have failed on its first push | A fresh session ran the tests with only the variables CI sets | The CI secret key was too short for the JWT library, which warns, and the tests fail on warnings. Longer key | 40, `cbe353a` |
| Two members taking the same task both got a 200, and the second kept it. An assignment could also slip between a member removal's two steps and leave a non-member assigned | A review of the finished code by a fresh model session: the check read an out-of-date object, and nothing locked a row | Taking a task is one conditional `UPDATE`; assignment and removal lock the membership row. Two tests, and two simultaneous requests on the running stack: one 200, one 409 | `test_two_members_taking_the_same_task_only_the_first_wins`, `test_assignment_and_member_removal_lock_the_membership_row` |
| The filter `assignee=²` answered 500 | Probing the running API with malformed input | `str.isdigit()` accepts "²" and `int()` then fails. Now `isdecimal()`, with a test | 40, `4314632` |
| With DEBUG off, the traceback of every server error was lost | The phase 1 walkthrough | A `LOGGING` setting, and a test that starts a fresh interpreter and checks the traceback reaches stderr | 13, `3f991c4` (test in `95f8965`) |
| mypy checked the code against the wrong Django: the type stubs described 6.1, the project runs 6.0 | Phase 2, on an admin method whose signature differs between the two | Stubs pinned to the 6.0 line | 19, `7ea1d39` |
| `is_overdue` returned NULL, not false, for a task without a due date | A test, before the commit | Fixed in the same phase | 17, `4ecec2a` |

The phase 1 walkthrough found nine issues in total, among them an image that shipped the package cache (807 MB
to 557 MB) and pre-commit hooks that were never installed (entry 13). The other two findings of the frontend
walkthrough: a deep link was lost at login, and the bell kept a fallback for an API that by then existed
(entry 34).

## 6. Edge cases, authentication and validation

The principle: a rule is checked where it cannot be skipped. A serializer checks the shape of the input. The
service checks the rule itself, whoever calls it: the API, the admin site or a job. Where the database can also
enforce it (unique memberships, `completed_at` matching the status), it does. Every rule has a test.

**Authentication.** Email login, stored lowercase. Access tokens last 15 minutes. Refresh tokens rotate and are
blacklisted on use, on logout and on a password change. A deactivated user cannot log in, and their open tokens
stop working. Login is limited to 5 tries per minute per client address.

**Validation and errors.** Every error has one JSON shape, `{code, message, details}`, with field details for
invalid input. A resource the caller cannot see answers 404; one they can see but may not change answers 403.

The cases I find most worth a look:

| Case | What happens | Test |
|---|---|---|
| Two members take the same unassigned task | The first gets it, the second gets 409 `already_assigned` | `tasks/tests/test_services.py::test_two_members_taking_the_same_task_only_the_first_wins` |
| A user created a task, then left the team | No rights on it any more | `tasks/tests/test_services.py::test_a_creator_who_left_...` |
| A member is removed while tasks are assigned to them | The tasks are unassigned in the same transaction | `test_services.py::test_member_removal_and_unassignment_...` |
| A client sends its own `X-Forwarded-For` | The login count is not reset | `accounts/tests/test_throttling.py::test_a_forged_forwarded_address_...` |
| A user is deactivated after logging in | Their token is rejected | `accounts/tests/test_auth_api.py::test_a_user_deactivated_after_login_is_rejected` |
| The overdue job runs twice | The second run sends nothing | `tasks/tests/test_overdue_job.py::test_a_second_run_...` |
| An overdue task has no assignee and its team has no leader | It stays unmarked until someone exists | `test_overdue_job.py::test_a_task_with_nobody_...` |
| The broker is down during an assignment | The assignment is kept, the notification is lost | `tasks/tests/test_assignment_notifications.py::test_a_broker_outage_...` |
| A notification job runs late, after the task was deleted or reassigned | Nothing is sent | `test_assignment_notifications.py::test_nothing_is_sent_for_a_task_deleted_or_reassigned_...` |
| Another tab rotated the refresh token first | The request retries with the new token | `frontend/src/api/client.test.ts` |
| A finished task is edited | 400 `task_finished`; reopen it first | `tasks/tests/test_api.py::test_finishing_then_editing_then_reopening` |

<details>
<summary>Every rule and the test that covers it</summary>

Phase 2 (entry 16):

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

Phase 6, demo seed (entries 28 and 30): its tests were removed with the seed code in entry 41; the demo data is
now plain SQL that no code knows about, checked on the running stack (entry 42).

Phase 7, frontend (entries 31 to 35):

| Rule | Covered by |
|---|---|
| Each task says whether the caller may edit or delete it, from the task policies | `backend/apps/tasks/tests/test_api.py::test_each_task_says_what_the_caller_may_do`, `::test_mutations_answer_the_permissions_of_the_caller` |
| Behind nginx, the login limit counts per client address; a forged header does not reset it | `backend/apps/accounts/tests/test_throttling.py::test_behind_one_proxy_...`, `::test_a_forged_forwarded_address_...` |
| Concurrent 401s share one token refresh; a refused refresh ends the session | `frontend/src/api/client.test.ts` ("token refresh") |
| A refresh refused because another tab rotated the token retries with the new one | `client.test.ts::retries with the token another tab stored meanwhile...` |
| Login and refresh calls never trigger a refresh; API errors keep their code, message and field details | `client.test.ts::never refreshes for the token endpoints...`, `client.test.ts` ("errors") |
| After login the user returns to the page asked for, never outside the app | `frontend/src/features/auth/returnPath.test.ts` |

</details>

## 7. Performance and idiomatic quality

Performance, each with its evidence:

- **List endpoints do not grow with the data.** The team list is one query and the task list two (count and
  page), whatever the number of rows. Tests fail if a change adds an N+1 (entries 16 and 17). The `can_edit` and
  `can_delete` flags reuse the role the task query already annotates, so they add no query.
- **The overdue job** reads the tasks and the leaders in two queries, writes one notification per person and
  team, and marks the tasks with one update (the code is in section 3).
- **Indexes were decided by measurement.** `EXPLAIN ANALYZE` on 200,000 generated tasks: a member's list takes 1
  to 5 ms with no index. A partial index would take the administrator's all-teams page from 90 ms to 0.3 ms. The
  model recommended no index; I agreed: "No index for now, keep it for later" (entry 29).

Idiomatic quality, first by tools (entry 12):

- mypy in strict mode plus `disallow_any_explicit`, with the Django and DRF plugins. Zero `# type: ignore` in
  the application code.
- ruff with the security (`S`), annotation (`ANN`), naive datetime (`DTZ`), Django (`DJ`) and bugbear (`B`)
  rule families.
- pytest fails on any warning and below 80% branch coverage.
- TypeScript in strict mode, eslint, vitest and the build are configured in CI next to the backend checks
  (entry 35).
- `manage.py check --deploy` on a fresh clone reports four warnings, all about HTTPS. The stack serves plain
  HTTP on localhost, so they belong to a deployment behind TLS (entry 37).

Tools do not judge taste, so these calls were mine:

- **An explicit call, not a signal,** between the teams and tasks apps (entry 10). A signal hides the behaviour.
- **No custom default manager for soft delete.** The filter is written in the selectors, where a reader sees it
  (soft delete: entry 9; the rule is in the implementation prompt).
- **A real column, not a JSON field,** for a team's `archive_after_days`. I asked about JSON; the model
  recommended the column and I agreed (design decisions table).
- **Version choices over novelty.** Django 6.0.10 and not 6.1, because drf-spectacular does not declare 6.1; a
  small typed environment reader, not one more dependency (entry 15).
- **The code must not know about demo data** (entry 41, section 5).
- **`apps/tasks/services.py` is too big.** Reading the finished code, I found it holds three things: the task
  rules, the assignment notification and the overdue job. Splitting it is in the backlog.
