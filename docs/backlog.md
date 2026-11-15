# Backlog

Ideas raised by the owner that are not in scope now. Each is checked against the base design first:
if it would change the foundation, it becomes a design topic instead of a backlog item.

## Tasks and teams

- Quotas: maximum tasks per team, members per team, teams led per user, open tasks per assignee.
  Owner wants to revisit soon. No concrete scenario defined yet.
- Limits configured by the team owner (leader). Related to team-level settings; depends on how team settings
  are stored (columns on Team versus a `TeamSettings` table).
- Custom statuses per team. Owner moved it to the backlog. Statuses start as a fixed list in code; moving to a
  per-team table later needs a data migration.
- Status history: record each status change (who, when, from, to). Owner asked for it after the reopen rule was
  agreed; the reopen action clears `completed_at`, so history would keep the full trail.
- Full audit trail (who changed which field, when), for example with history tables. For now only soft delete
  covers restorable deletes.
- Periodic archiving job or archive table. Not needed while archiving is derived from `completed_at`.
- Notify admins when a team loses its last leader. Dropped to simplify; admins use the orphan teams filter instead.

## Accounts and members

- Public register endpoint and password reset by email. Not in the requirements; users are created by admins for now.
- Do not reveal which emails have accounts when a leader adds a member (owner's choice, option "a"). Every add
  answers 202 with the same body and creates a pending invitation for the email; it becomes a membership at the
  user's next login or when an admin creates the account, so existing and unknown emails look the same to the
  leader. Needs an `Invitation` table, list and cancel endpoints, and a hook at login and at account creation.
  Until then, an unknown or inactive email answers 404 `user_not_found`.
- Follow-up: the invited user accepts or declines the invitation instead of joining automatically.

## Frontend

- Drag and drop on the task board (move a card between columns to change its status). For now the status changes
  through a control on the card.
- Keep the board filters in the URL, so they survive a reload and can be shared as a link (the open task already
  is, as `?task=`).
- A change-password screen in the frontend. The endpoint exists (`/api/v1/auth/password`) and revokes older
  tokens; the UI does not offer it yet.
- If the API is unreachable when the app loads, the login form shows although the stored session is still valid
  (a reload recovers it). Show an error with a Retry button instead when the failure is not a 401.

## Known limits

- Detect lost updates: today the last save wins when two people edit the same task. Send the `updated_at` read
  (or an ETag) with each change and answer 409 when the task changed in between.
- Cursor pagination for the board columns. "Load more" asks by page number, so a task that moves while someone
  pages can show twice (filtered out on screen) or be skipped until the next refresh.
- With Redis fully down, login answers 500 as an HTML page: the rate limit counts in Redis. Decide whether the
  limit fails open (allow) or closed (refuse with 503), and make unhandled 500s use the JSON error shape.

## Performance and deployment

- Partial index on tasks `(due_date, id)` for the admin all-teams list: 90 ms to 0.3 ms on 200k tasks (journal
  entry 29). Not added while the member path is already fast.
- Deployment settings for HTTPS, switched on by one environment variable: HSTS, SSL redirect, secure session and
  CSRF cookies (the four `manage.py check --deploy` warnings). Off for the local HTTP demo.
- Serve the Swagger UI assets from the app (for example drf-spectacular-sidecar) instead of a public CDN, so the
  API docs work offline.

## Code quality and tests

- Split `apps/tasks/services.py`. It holds three things: the task rules, the assignment notification and the
  overdue job, plus two type declarations (`TaskChanges`, `OverdueRun`). Move the notification code to its own
  module and the types out of the service file, so the service reads as the task rules only. Raised by the owner
  on reading the finished code.
- Automated browser check (for example a Playwright smoke test) that fails on any console warning. For now the
  owner checks the console by hand.
