-- Demo teams. "Design Guild" has no leader; "Legacy Migration" is soft-deleted (its tasks
-- must never show up in any list). Safe to run twice: matched by name and deleted state.
INSERT INTO teams_team (name, archive_after_days, deleted_at, deleted_by_id, created_at, updated_at)
SELECT v.name, v.archive_after_days,
       CASE WHEN v.deleted THEN now() - interval '10 days' END,
       CASE WHEN v.deleted THEN (SELECT id FROM accounts_user WHERE email = 'admin@example.com') END,
       now(), now()
FROM (VALUES
    ('Platform',         15, FALSE),
    ('Mobile App',        7, FALSE),
    ('Design Guild',     15, FALSE),
    ('Legacy Migration', 15, TRUE)
) AS v(name, archive_after_days, deleted)
WHERE NOT EXISTS (
    SELECT 1 FROM teams_team t
    WHERE t.name = v.name AND (t.deleted_at IS NOT NULL) = v.deleted
);
