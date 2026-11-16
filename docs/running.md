# Running and developing

The short version is in the [README](../README.md). Demo accounts and sample data:
[`demo-data.md`](demo-data.md).

## What `./run.sh up` does

On the first start it copies `.env.example` to `.env`. Then it builds the images and starts everything:
PostgreSQL, Redis, a one-shot `migrate` service that applies the migrations, a one-shot `seed` service that loads the
demo SQL files unless `--no-seed` is given (safe to run again), the API (gunicorn), the Celery worker and beat, and nginx serving the frontend.
When every service is healthy it prints the URLs.

`--no-seed` (Windows: `-NoSeed`) only skips loading; it does not remove demo data already in the database volume.
For an empty database, drop the volume first: `docker compose down -v`, then `./run.sh up --no-seed`.

Without the wrappers: `cp .env.example .env`, then `docker compose up --build -d --wait` (add `SEED_DEMO=0` in front
to skip the seed).

Verified on Linux (WSL2 on Windows, Docker Engine). `run.ps1` (Windows PowerShell) mirrors `run.sh` but has not been
tested.

## URLs

Everything goes through nginx on one port (`FRONTEND_PORT`, default 8080). The API container is not published on
the host on purpose (see "Rate limiting" in [README Part 2](../README.md#part-2-user-story-and-design)).

| What | URL |
|---|---|
| Web app | http://localhost:8080/ |
| API | http://localhost:8080/api/v1/ |
| Swagger UI / OpenAPI schema | http://localhost:8080/api/v1/docs / http://localhost:8080/api/v1/schema |
| Django admin site | http://localhost:8080/admin/ |
| Health check | http://localhost:8080/api/v1/health |

## Connect to PostgreSQL (DBeaver or any client)

PostgreSQL is published on the host. Use the values from `.env`:

| Setting | Value (defaults from `.env.example`) |
|---|---|
| Host | `localhost` |
| Port | `POSTGRES_PORT` (5432) |
| Database | `POSTGRES_DB` (`taskmanager`) |
| User | `POSTGRES_USER` (`taskmanager`) |
| Password | `POSTGRES_PASSWORD` (`demo-only-password`) |

## Tests and checks

```sh
./run.sh test                                 # backend: pytest with coverage (fails below 80%)

cd backend && uv sync                         # backend outside Docker (needs the stack's PostgreSQL)
set -a; . ../.env; set +a
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy .

cd frontend && npm ci                         # frontend
npm run lint && npm test && npm run build     # eslint, vitest, then tsc and the production build
```

`pre-commit install` (from the repo root) runs ruff, ruff format, mypy (strict) and file checks on each commit.
CI (`.github/workflows/ci.yml`) runs the backend and frontend checks on pushes to `main`.

## Run the overdue job on demand

Celery beat runs it daily at `OVERDUE_JOB_TIME` (default 08:00, in `TIME_ZONE`). To run it now:

```sh
docker compose exec api python manage.py notify_overdue
```

It prints how many notifications it sent. A second run sends nothing new.

## Frontend development

`docker compose` serves a production build. For hot reload, keep the stack running and start the Vite dev server,
which forwards `/api` to it:

```sh
cd frontend && npm ci && npm run dev          # http://localhost:5173
```

## Project structure

```
backend/
  config/            settings (all from environment variables), URLs, Celery app
  apps/
    core/            base model (timestamps), domain exceptions, the single API error handler, health
    accounts/        custom user (email login), JWT auth endpoints, rate limits
    teams/           teams, memberships and roles, Django admin site
    notifications/   stores and delivers notifications (knows no task rule)
    tasks/           tasks, their rules, the overdue job, the assignment notification
  seed/              the demo data as SQL files, loaded by psql (docs/demo-data.md)
  Each app: models.py, services.py (the only write path), selectors.py (reads), policies.py (permissions),
  serializers.py and views.py (thin API layer), tests/
frontend/
  src/api/           the one HTTP client (tokens, refresh, errors) and typed endpoints
  src/features/      auth, teams, tasks, notifications: pages, components and their queries
  src/components/    shared UI pieces
  nginx.conf         serves the build, proxies /api, /admin and /static to the api
docs/                requirements, implementation prompt, GenAI journal, backlog
docker-compose.yml   the whole stack; run.sh and run.ps1 are thin wrappers around it
```
