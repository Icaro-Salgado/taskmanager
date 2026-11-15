# syntax=docker/dockerfile:1
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

# Unprivileged user that owns the code and runs the app.
RUN useradd --create-home --uid 1000 app && mkdir /app && chown app:app /app
WORKDIR /app

# Dependencies first, so this layer is rebuilt only when the lock file changes.
# The dev group is installed too: `run.sh test` runs the tests inside this image.
# uv's download cache lives in a build cache mount, so it never ends up in the image.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

COPY --chown=app:app . .
USER app

# Build-time placeholders only: collectstatic needs settings to import, not real values.
RUN DJANGO_SECRET_KEY=build-only POSTGRES_PASSWORD=build-only python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
