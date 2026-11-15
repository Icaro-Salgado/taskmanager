# Backlog

Ideas raised by the owner that are not in scope now. Each is checked against the base design first:
if it would change the foundation, it becomes a design topic instead of a backlog item.

- Quotas: maximum tasks per team, members per team, teams led per user, open tasks per assignee.
  Owner wants to revisit soon. No concrete scenario defined yet.
- Limits configured by the team owner (leader). Related to team-level settings; depends on how team settings
  are stored (columns on Team versus a `TeamSettings` table).
- Custom statuses per team. Owner moved it to the backlog. Statuses start as a fixed list in code; moving to a
  per-team table later needs a data migration.
- Status history: record each status change (who, when, from, to). Owner asked for it after the reopen rule was
  agreed; the reopen action clears `completed_at`, so history would keep the full trail.
- Public register endpoint and password reset by email. Not in the requirements; users are created by admins for now.
- Notify admins when a team loses its last leader. Dropped to simplify; admins use the orphan teams filter instead.
- Periodic archiving job or archive table. Not needed while archiving is derived from `completed_at`.
- Automated browser check (for example a Playwright smoke test) that fails on any console warning. For now the
  owner checks the console by hand.
- Full audit trail (who changed which field, when), for example with history tables. For now only soft delete
  covers restorable deletes.
- Drag and drop on the task board (move a card between columns to change its status). For now the status changes
  through a control on the card.
