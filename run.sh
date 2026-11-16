#!/usr/bin/env sh
# Thin wrapper around Docker Compose. Usage: ./run.sh [up [--no-seed]|down|test]
# Details: docs/running.md
set -eu
cd "$(dirname "$0")"

ensure_env() {
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
    fi
}

read_env() {
    grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-
}

case "${1:-up}" in
    up)
        ensure_env
        seed=1
        if [ "${2:-}" = "--no-seed" ]; then
            seed=0
        elif [ -n "${2:-}" ]; then
            echo "Unknown option: $2 (expected --no-seed)" >&2
            exit 1
        fi
        SEED_DEMO=$seed docker compose up --build -d --wait
        base="http://localhost:$(read_env FRONTEND_PORT)"
        [ "$base" = "http://localhost:" ] && base="http://localhost:8080"
        echo
        echo "App:          ${base}/"
        echo "API:          ${base}/api/v1/"
        echo "Health:       ${base}/api/v1/health"
        echo "Swagger UI:   ${base}/api/v1/docs"
        echo "Django admin: ${base}/admin/"
        if [ "$seed" = 1 ]; then echo "Demo logins:  seed/README.md (demo only)"; fi
        ;;
    down)
        docker compose down
        ;;
    test)
        ensure_env
        docker compose run --build --rm api pytest
        ;;
    *)
        echo "Usage: $0 [up [--no-seed]|down|test]" >&2
        exit 1
        ;;
esac
