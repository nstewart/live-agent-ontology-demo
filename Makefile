.PHONY: help setup up down logs clean migrate seed reset-db test lint

# Default target
help:
	@echo "FreshMart Digital Twin - Available Commands"
	@echo "============================================"
	@echo ""
	@echo "Setup & Run:"
	@echo "  make setup      - Initial setup (copy .env, build containers)"
	@echo "  make up         - Start all services"
	@echo "  make up-agent   - Start all services including agent"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - Tail logs from all services"
	@echo "  make logs-api   - Tail logs from API service"
	@echo ""
	@echo "Database:"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed demo data"
	@echo "  make reset-db   - Reset database (WARNING: destroys data)"
	@echo ""
	@echo "Development:"
	@echo "  make test       - Run all tests"
	@echo "  make test-api   - Run API tests"
	@echo "  make test-web   - Run Web UI tests"
	@echo "  make lint       - Run linters"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean      - Remove all containers, volumes, and build artifacts"
	@echo "  make shell-db   - Open psql shell to main database"
	@echo "  make shell-mz   - Open psql shell to Materialize emulator"
	@echo "  make shell-api  - Open bash shell in API container"

# Setup
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	fi
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  - API:        http://localhost:$${API_PORT:-8080}"
	@echo "  - Web UI:     http://localhost:$${WEB_PORT:-5173}"
	@echo "  - PostgreSQL: localhost:$${PG_PORT:-5432}"
	@echo "  - OpenSearch: http://localhost:$${OS_PORT:-9200}"
	@echo ""
	@echo "Run 'make logs' to see service output"

up-agent:
	docker-compose --profile agent up -d

down:
	docker-compose --profile agent down

# Logs
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-sync:
	docker-compose logs -f search-sync

# Database
migrate:
	./db/scripts/run_migrations.sh

seed:
	./db/scripts/seed_demo.sh

reset-db:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v
	docker volume rm freshmart-digital-twin-agent-starter_postgres_data || true
	docker volume rm freshmart-digital-twin-agent-starter_materialize_data || true
	docker-compose up -d db mz
	@echo "Waiting for databases to be ready..."
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed

# Testing
test: test-api test-web

test-api:
	docker-compose exec api pytest -v

test-web:
	docker-compose exec web npm test

# Linting
lint:
	docker-compose exec api ruff check src/
	docker-compose exec web npm run lint

# Cleanup
clean:
	docker-compose --profile agent down -v --rmi local
	rm -rf api/__pycache__ api/.pytest_cache
	rm -rf search-sync/__pycache__
	rm -rf agents/__pycache__
	rm -rf web/node_modules web/dist

# Shell access
shell-db:
	docker-compose exec db psql -U $${PG_USER:-postgres} -d $${PG_DATABASE:-freshmart}

shell-mz:
	docker-compose exec mz psql -U $${MZ_USER:-materialize} -d $${MZ_DATABASE:-materialize}

shell-api:
	docker-compose exec api /bin/bash

# Health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:$${API_PORT:-8080}/health | jq . || echo "API: Not responding"
	@curl -s http://localhost:$${OS_PORT:-9200}/_cluster/health | jq . || echo "OpenSearch: Not responding"
