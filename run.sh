#!/usr/bin/env sh
# Thin wrapper around Docker Compose. Usage: ./run.sh [up|down|test]
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
        docker compose up --build -d --wait
        base="http://localhost:$(read_env FRONTEND_PORT)"
        [ "$base" = "http://localhost:" ] && base="http://localhost:8080"
        echo
        echo "App:          ${base}/"
        echo "API:          ${base}/api/v1/"
        echo "Health:       ${base}/api/v1/health"
        echo "Swagger UI:   ${base}/api/v1/docs"
        echo "Django admin: ${base}/admin/"
        echo "Demo logins:  README.md, section \"Demo credentials\" (demo only)"
        ;;
    down)
        docker compose down
        ;;
    test)
        ensure_env
        docker compose run --build --rm api pytest
        ;;
    *)
        echo "Usage: $0 [up|down|test]" >&2
        exit 1
        ;;
esac
