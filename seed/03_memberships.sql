-- Demo memberships. Ana leads Platform but is only a member of Mobile App.
INSERT INTO teams_membership (team_id, user_id, role, created_at, updated_at)
SELECT t.id, u.id, v.role, now(), now()
FROM (VALUES
    ('Platform',         'ana@example.com',   'leader'),
    ('Platform',         'bruno@example.com', 'member'),
    ('Platform',         'carla@example.com', 'member'),
    ('Platform',         'diego@example.com', 'member'),
    ('Mobile App',       'carla@example.com', 'leader'),
    ('Mobile App',       'ana@example.com',   'member'),
    ('Mobile App',       'fabio@example.com', 'member'),
    ('Design Guild',     'eva@example.com',   'member'),
    ('Design Guild',     'gabi@example.com',  'member'),
    ('Legacy Migration', 'bruno@example.com', 'leader'),
    ('Legacy Migration', 'diego@example.com', 'member')
) AS v(team, email, role)
JOIN teams_team t ON t.name = v.team
JOIN accounts_user u ON u.email = v.email
ON CONFLICT (team_id, user_id) DO NOTHING;
