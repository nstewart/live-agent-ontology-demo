#!/bin/bash
# Run database migrations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" -f "$migration"
    fi
done

echo "Migrations complete!"
