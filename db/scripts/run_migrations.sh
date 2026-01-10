#!/bin/bash
# Run database migrations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect docker compose command (prefer "docker compose" over "docker-compose")
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Default values
PG_HOST=${PG_HOST:-localhost}
PG_PORT=${PG_PORT:-5432}
PG_USER=${PG_USER:-postgres}
PG_PASSWORD=${PG_PASSWORD:-postgres}
PG_DATABASE=${PG_DATABASE:-freshmart}

export PGPASSWORD=$PG_PASSWORD

echo "Running migrations against $PG_HOST:$PG_PORT/$PG_DATABASE..."

# Run migrations in order
for migration in "$SCRIPT_DIR/../migrations"/*.sql; do
    if [ -f "$migration" ]; then
        filename=$(basename "$migration")
        echo "Applying migration: $filename"
        # Use psql from Docker container to avoid requiring local psql installation
        $DOCKER_COMPOSE exec -T db psql -U "$PG_USER" -d "$PG_DATABASE" -f "/docker-entrypoint-initdb.d/migrations/$filename"
    fi
done

echo "Migrations complete!"
