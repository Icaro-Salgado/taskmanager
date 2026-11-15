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
        api_port="$(read_env API_PORT)"
        frontend_port="$(read_env FRONTEND_PORT)"
        echo
        echo "App:          http://localhost:${frontend_port:-8080}/"
        echo "API:          http://localhost:${api_port:-8000}/api/v1/"
        echo "Health:       http://localhost:${api_port:-8000}/api/v1/health"
        echo "Swagger UI:   http://localhost:${api_port:-8000}/api/v1/docs"
        echo "Django admin: http://localhost:${api_port:-8000}/admin/"
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
