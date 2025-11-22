#!/bin/bash
# Seed demo data

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

echo "Seeding demo data into $PG_HOST:$PG_PORT/$PG_DATABASE..."

# Run seed files in order
for seed in "$SCRIPT_DIR/../seed"/*.sql; do
    if [ -f "$seed" ]; then
        filename=$(basename "$seed")
        echo "Running seed: $filename"
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" -f "$seed"
    fi
done

# Refresh Materialize views
MZ_HOST=${MZ_HOST:-localhost}
MZ_PORT=${MZ_PORT:-6875}
MZ_USER=${MZ_USER:-materialize}
MZ_PASSWORD=${MZ_PASSWORD:-materialize}
MZ_DATABASE=${MZ_DATABASE:-materialize}

export PGPASSWORD=$MZ_PASSWORD

echo "Refreshing Materialize views..."
psql -h "$MZ_HOST" -p "$MZ_PORT" -U "$MZ_USER" -d "$MZ_DATABASE" -c "SELECT refresh_all_views();" 2>/dev/null || echo "Note: Materialize refresh skipped (service may not be ready)"

echo "Seed complete!"
