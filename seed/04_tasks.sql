-- Demo tasks. Dates are relative to today, so the demo looks right whenever it is loaded:
-- `due` is days from today (negative is overdue), `finished` is days ago (done and canceled only).
-- Platform has more than 20 active tasks, so its list paginates. Each task is created by its
-- team's leader (Design Guild has none: Eva). Safe to run twice: matched by team and title.
INSERT INTO tasks_task (team_id, title, description, status, created_by_id, assignee_id,
                        due_date, completed_at, created_at, updated_at)
SELECT t.id, v.title, v.description, v.status, c.id, a.id,
       CURRENT_DATE + v.due,
       now() - make_interval(days => v.finished),
       now(), now()
FROM (VALUES
    -- team, title, status, assignee, due, finished, description
    ('Platform', 'Upgrade PostgreSQL to 17', 'in_progress', 'bruno', 5, NULL, 'Rehearse the upgrade on staging first.'),
    ('Platform', 'Add rate limiting to the public API', 'in_progress', 'ana', 2, NULL, ''),
    ('Platform', 'Rotate the staging database credentials', 'todo', 'diego', -3, NULL, 'Was due last week; the old ones are still valid.'),
    ('Platform', 'Write the incident runbook for failed deploys', 'todo', 'carla', 10, NULL, ''),
    ('Platform', 'Fix flaky integration test in billing', 'blocked', 'bruno', -1, NULL, 'Waiting for a CI runner with more memory.'),
    ('Platform', 'Move the build cache to the shared runner', 'todo', NULL, 14, NULL, ''),
    ('Platform', 'Document the on-call handover', 'todo', NULL, NULL, NULL, ''),
    ('Platform', 'Replace the deprecated logging library', 'in_progress', 'diego', 7, NULL, ''),
    ('Platform', 'Set up error budget dashboards', 'todo', 'carla', 21, NULL, ''),
    ('Platform', 'Audit service account permissions', 'blocked', 'ana', -6, NULL, 'Needs the security team to export the access report.'),
    ('Platform', 'Reduce the Docker image size', 'in_progress', NULL, 9, NULL, ''),
    ('Platform', 'Enable dependency vulnerability scanning', 'todo', 'bruno', -10, NULL, ''),
    ('Platform', 'Plan the Redis failover test', 'todo', 'diego', 30, NULL, ''),
    ('Platform', 'Archive old build artifacts', 'todo', NULL, 3, NULL, ''),
    ('Platform', 'Review the backup retention policy', 'todo', 'ana', 12, NULL, ''),
    ('Platform', 'Migrate the cron jobs to the scheduler', 'in_progress', 'carla', 4, NULL, ''),
    ('Platform', 'Investigate the slow query on the reports page', 'blocked', NULL, -2, NULL, ''),
    ('Platform', 'Publish the architecture overview', 'todo', 'carla', 1, NULL, ''),
    ('Platform', 'Tune the database connection pool', 'todo', NULL, -15, NULL, ''),
    ('Platform', 'Check TLS certificate expiry dates', 'in_progress', 'ana', 0, NULL, ''),
    ('Platform', 'Add health checks to the worker', 'done', 'bruno', NULL, 2, ''),
    ('Platform', 'Pin base image versions', 'done', 'diego', NULL, 6, ''),
    ('Platform', 'Set up the staging environment', 'done', 'ana', NULL, 40, ''),
    ('Platform', 'Remove unused feature flags', 'done', 'carla', NULL, 25, ''),
    ('Platform', 'Introduce structured logging', 'done', 'bruno', NULL, 60, ''),
    ('Platform', 'Evaluate a second cloud region', 'canceled', NULL, NULL, 3, 'Out of budget this year.'),
    ('Platform', 'Switch to a managed Kafka', 'canceled', 'diego', NULL, 45, ''),
    ('Platform', 'Rewrite the deploy script in Go', 'canceled', NULL, NULL, 90, ''),
    ('Mobile App', 'Fix the crash when opening a task offline', 'in_progress', 'fabio', 3, NULL, ''),
    ('Mobile App', 'Add dark mode to the task list', 'todo', 'ana', 15, NULL, ''),
    ('Mobile App', 'Support push notification deep links', 'blocked', 'fabio', -4, NULL, ''),
    ('Mobile App', 'Release 2.4 to the app stores', 'todo', 'carla', 6, NULL, ''),
    ('Mobile App', 'Reduce startup time on older phones', 'todo', NULL, 20, NULL, ''),
    ('Mobile App', 'Replace the date picker', 'done', 'ana', NULL, 1, ''),
    ('Mobile App', 'Update the onboarding screens', 'done', 'fabio', NULL, 12, ''),
    ('Mobile App', 'Drop support for Android 8', 'canceled', NULL, NULL, 20, ''),
    ('Design Guild', 'Refresh the icon set', 'in_progress', 'gabi', 8, NULL, ''),
    ('Design Guild', 'Write the accessibility checklist', 'todo', 'eva', -2, NULL, ''),
    ('Design Guild', 'Audit color contrast on the dashboard', 'todo', NULL, NULL, NULL, ''),
    ('Design Guild', 'Publish the spacing guidelines', 'done', 'eva', NULL, 5, ''),
    ('Legacy Migration', 'Freeze writes to the old billing system', 'done', 'bruno', NULL, 50, ''),
    ('Legacy Migration', 'Decommission the old VPN', 'todo', 'diego', 30, NULL, '')
) AS v(team, title, status, assignee, due, finished, description)
JOIN teams_team t ON t.name = v.team
JOIN (VALUES
    ('Platform', 'ana'), ('Mobile App', 'carla'), ('Design Guild', 'eva'), ('Legacy Migration', 'bruno')
) AS creator(team, name) ON creator.team = v.team
JOIN accounts_user c ON c.email = creator.name || '@example.com'
LEFT JOIN accounts_user a ON a.email = v.assignee || '@example.com'
WHERE NOT EXISTS (SELECT 1 FROM tasks_task x WHERE x.team_id = t.id AND x.title = v.title);
