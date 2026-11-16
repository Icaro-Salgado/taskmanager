-- Demo users. DEMO ONLY: every account shares the public password "Demo-only-pass-2026"
-- (stored below as its Django hash). Never load this file outside a local demo database.
-- Safe to run twice: an email that already exists is skipped, so a changed password is kept.
INSERT INTO accounts_user (email, password, is_superuser, is_staff, is_active, created_at, updated_at)
SELECT v.email,
       'pbkdf2_sha256$1200000$demoonlysalt2026$THHyR+rgaTJH6xWN/IHqc3EgW+nbjkGhC5E8pOgw++w=',
       v.admin, v.admin, TRUE, now(), now()
FROM (VALUES
    ('admin@example.com', TRUE),
    ('ana@example.com',   FALSE),
    ('bruno@example.com', FALSE),
    ('carla@example.com', FALSE),
    ('diego@example.com', FALSE),
    ('eva@example.com',   FALSE),
    ('fabio@example.com', FALSE),
    ('gabi@example.com',  FALSE)
) AS v(email, admin)
WHERE NOT EXISTS (SELECT 1 FROM accounts_user u WHERE u.email = v.email);
