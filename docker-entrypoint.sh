#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL must be set before starting the app." >&2
    exit 1
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
