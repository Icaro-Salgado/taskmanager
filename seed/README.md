# Seed: demo data (demo only)

Everything about the demo data lives in this folder; the application code knows nothing about it.

The sample data is the SQL files here, loaded in name order with
`psql` by the one-shot `seed` service in `docker-compose.yml`, right after the migrations (`./run.sh up --no-seed`
skips it). No application code is involved.
Each statement inserts only the rows whose natural key (email, team name, team and task title) is missing, so
loading twice creates nothing and an edited demo record is kept. Dates are relative to the day of loading, so
overdue and archived tasks look right whenever the demo is first started.

The rows go straight into the tables, not through the services: the demo needs tasks finished weeks ago and a team
that is already deleted, which the services refuse to create. A consequence: loading the seed sends no
notifications.

| File | Content |
|---|---|
| `01_users.sql` | The administrator and seven users |
| `02_teams.sql` | Four teams, one with no leader and one soft-deleted |
| `03_memberships.sql` | Who is in which team, and as what |
| `04_tasks.sql` | 42 tasks covering every status, overdue, unassigned and archived ones |

To change the demo, edit these files and reload on an empty database (`docker compose down -v`, then `./run.sh up`).

## Accounts

**The password is public and for local demo use only.** All accounts share it: `Demo-only-pass-2026` (stored in
`01_users.sql` as its Django hash).

| Account | Role |
|---|---|
| `admin@example.com` | Administrator: sees every team, uses the Django admin site |
| `ana@example.com` | Leader of Platform, member of Mobile App |
| `carla@example.com` | Leader of Mobile App, member of Platform |
| `bruno@example.com` | Member of Platform, leader of Legacy Migration (a deleted team) |
| `diego@example.com`, `fabio@example.com` | Members |
| `eva@example.com`, `gabi@example.com` | Members of Design Guild, a team with no leader |

The Platform team has more than 20 active tasks, so its board paginates.
