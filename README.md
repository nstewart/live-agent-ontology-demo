# FreshMart Digital Twin Agent Starter

A production-ready starter for building semantic knowledge graphs with real-time materialized views, AI agents, and full-text search.

## What Is This?

FreshMart demonstrates a **digital twin** of same-day grocery delivery operations powered by:

- **PostgreSQL** as a governed triple store with ontology-based validation
- **Materialize** for real-time CQRS read models with sub-second CDC
- **OpenSearch** for natural language search over orders and inventory
- **LangGraph Agents** with semantic reasoning over the knowledge graph
- **React Admin UI** with WebSocket-powered real-time updates

## Who Is This For?

- Teams building **semantic knowledge graphs** that need ACID guarantees
- Projects requiring **real-time materialized views** over graph data
- Organizations exploring **CQRS patterns** with ontology validation
- Developers building **AI agents** that reason over operational data
- Anyone wanting a **batteries-included starter** for graph-backed applications

## Quick Start

```bash
# Clone and configure
git clone https://github.com/your-org/freshmart-digital-twin-agent-starter.git
cd freshmart-digital-twin-agent-starter
cp .env.example .env

# Start all services (auto-initializes everything)
make up

# Or start with AI agent included
make up-agent
```

**Services will be ready at:**
- Admin UI: http://localhost:5173
- API Docs: http://localhost:8080/docs
- Materialize Console: http://localhost:6874
- OpenSearch: http://localhost:9200

The system automatically seeds demo data: 5 stores, 15 products, 15 customers, 20 orders.

## Core Features

### Real-Time Data Synchronization
- **Sub-second CDC** from PostgreSQL to Materialize via Debezium
- **Differential streaming** to UI clients via Zero WebSocket protocol
- **Automatic reconciliation** across all connected interfaces
- Changes appear in UI, search indexes, and materialized views simultaneously

### Semantic Knowledge Graph
- **RDF-style triples** (subject-predicate-object) as universal data model
- **Ontology validation** enforces schema at write time
- **Class and property definitions** prevent invalid data entry
- **Entity references** maintain graph relationships with referential integrity

### CQRS Architecture
- **Write model**: PostgreSQL triple store with ontology validation
- **Read model**: Materialize materialized views optimized per query pattern
- **Independent scaling** of writes (PostgreSQL) and reads (Materialize)
- **Real-time consistency** maintained via CDC with millisecond latency

### Dynamic Pricing Engine
- **Zone-based adjustments**: Manhattan (+15%), Brooklyn (+5%), baseline Queens
- **Perishability discounts**: 5% off to move inventory faster
- **Local scarcity premiums**: +10% for items with low store stock
- **Demand multipliers**: Real-time pricing based on sales velocity
- **Live price display** in UI shopping cart and order creation

### AI-Powered Operations
- **Natural language search** over orders and inventory via OpenSearch
- **LangGraph agents** with tools for semantic reasoning
- **Conversational memory** with PostgreSQL-backed checkpointing
- **Write operations** agents can create customers, orders, and update statuses
- **Read operations** agents can search, fetch context, and analyze data

### Full-Text Search
- **Orders index**: Search by customer name, address, order number, status
- **Inventory index**: Search by product name, category, store, ingredients
- **Real-time sync**: < 2 second latency from write to searchable
- **SUBSCRIBE streaming**: Differential updates from Materialize to OpenSearch

## Architecture Overview

FreshMart implements **CQRS (Command Query Responsibility Segregation)** to separate write and read concerns:

**Write Path:**
All data modifications flow through the PostgreSQL triple store where they are validated against the ontology schema (classes, properties, ranges, domains). This ensures semantic consistency and referential integrity at write time.

**Read Path:**
Queries use Materialize materialized views that are pre-computed, denormalized, and indexed in a three-tier architecture (ingest cluster for CDC, compute cluster for aggregation, serving cluster for indexed queries). Views update in real-time via Change Data Capture.

**Benefits:**
- Write model enforces schema through ontology validation
- Read model optimized for specific query patterns (orders, inventory, customers)
- Real-time consistency via CDC ensures views reflect writes within milliseconds
- Independent scaling of write and read workloads

**Data Flow:**
```
User → API → PostgreSQL (validated write)
              ↓ CDC
              Materialize (materialized views)
              ↓ SUBSCRIBE
              Zero Server → WebSocket → UI (live updates)
              ↓ SUBSCRIBE
              Search Sync → OpenSearch (full-text search)
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed component descriptions and data flow diagrams.

## API Overview

The Graph API (FastAPI, port 8080) provides three main categories of endpoints:

**Ontology Management (`/ontology`)**
Define and manage schema classes and properties. Control what entity types exist and what predicates are valid for each class.

**Triple Store CRUD (`/triples`)**
Manage knowledge graph data as subject-predicate-object triples. All writes are validated against the ontology before persistence.

**FreshMart Operations (`/freshmart`)**
Query pre-computed, denormalized views powered by Materialize. Includes orders, stores, inventory, customers, products, and couriers.

See [API_REFERENCE.md](docs/API_REFERENCE.md) for complete endpoint documentation with examples.

## Using the AI Agent

### Prerequisites

Add an LLM API key to your `.env` file:

```bash
# Option 1: Anthropic (recommended)
ANTHROPIC_API_KEY=sk-ant-...

# Option 2: OpenAI
OPENAI_API_KEY=sk-...
```

### Start Agent Service

```bash
# Using make (handles initialization)
make up-agent

# Or using docker-compose directly
docker-compose --profile agent up -d
docker-compose exec agents python -m src.init_checkpointer
```

### Interactive Chat

```bash
# Start interactive session with conversation memory
docker-compose exec -it agents python -m src.main chat

# Example conversation:
> Find orders for Lisa
> Show me her orders that are out for delivery
> Mark order FM-1001 as DELIVERED
> Create an order for John at Brooklyn store with milk and eggs
```

### Single Command

```bash
# One-time query
docker-compose exec agents python -m src.main chat "Show all OUT_FOR_DELIVERY orders"

# Search inventory
docker-compose exec agents python -m src.main chat "Find stores with organic milk in stock"
```

See [AGENTS.md](docs/AGENTS.md) for complete agent capabilities, tool descriptions, and HTTP API usage.

## Services

| Service | Port | Description |
|---------|------|-------------|
| **db** | 5432 | PostgreSQL - primary triple store |
| **mz** | 6874 | Materialize Admin Console |
| **mz** | 6875 | Materialize SQL interface |
| **zero-server** | 8090 | WebSocket server for real-time UI updates |
| **opensearch** | 9200 | Search engine for orders and inventory |
| **api** | 8080 | FastAPI backend |
| **search-sync** | - | Dual SUBSCRIBE workers for OpenSearch sync |
| **web** | 5173 | React admin UI with real-time updates |
| **agents** | 8081 | LangGraph agent runner (optional) |

## Development

### Essential Commands

```bash
# Start all services
make up

# Start with agents
make up-agent

# Stop services (data persists)
make down

# View logs
docker-compose logs -f api
docker-compose logs -f search-sync

# Restart a service
docker-compose restart api

# Run tests
docker-compose exec api python -m pytest tests/ -v

# See all commands
make help
```

### Generate Load Test Data

```bash
# Generate ~700K triples (6 months of operations)
./db/scripts/generate_data.sh

# Or smaller dataset for quick testing
./db/scripts/generate_data.sh --scale 0.1
```

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup, testing guidelines, and contribution workflow.

## Project Structure

```
freshmart-digital-twin-agent-starter/
├── docker-compose.yml          # Service orchestration
├── Makefile                    # Common commands
├── .env.example                # Environment template
│
├── db/
│   ├── migrations/             # SQL migrations
│   ├── seed/                   # Demo data
│   ├── materialize/            # Materialize initialization
│   └── scripts/                # Load test data generator
│
├── api/                        # FastAPI backend
│   ├── src/
│   │   ├── ontology/          # Ontology CRUD
│   │   ├── triples/           # Triple store + validation
│   │   ├── freshmart/         # Operational endpoints
│   │   └── routes/            # HTTP routes
│   └── tests/                  # Unit and integration tests
│
├── search-sync/               # OpenSearch sync workers
│   └── src/
│       ├── base_subscribe_worker.py  # Abstract base class
│       ├── orders_sync.py     # Orders sync worker
│       └── inventory_sync.py  # Inventory sync worker
│
├── zero-server/               # WebSocket server
│   └── src/
│       ├── server.ts          # Zero protocol WebSocket server
│       └── materialize-backend.ts  # SUBSCRIBE to Materialize
│
├── web/                       # React admin UI
│   └── src/
│       ├── api/               # API client
│       ├── hooks/             # useZeroQuery for real-time data
│       └── pages/             # Orders, Couriers, Stores dashboards
│
├── agents/                    # LangGraph agents
│   └── src/
│       ├── tools/             # Agent tools
│       └── graphs/            # LangGraph definitions
│
└── docs/                      # Documentation
```

## Documentation Index

### Core Concepts
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture, data flow, and component details
- [ONTOLOGY.md](docs/ONTOLOGY.md) - Ontology design patterns and extending the schema
- [DATA_MODEL.md](docs/DATA_MODEL.md) - Triple store model, entity types, and relationships

### Implementation Guides
- [SEARCH.md](docs/SEARCH.md) - OpenSearch setup, sync architecture, and debugging
- [AGENTS.md](docs/AGENTS.md) - AI agent capabilities, tools, and integration patterns
- [MATERIALIZE.md](docs/MATERIALIZE.md) - Materialize views, indexes, and three-tier architecture
- [REAL_TIME.md](docs/REAL_TIME.md) - WebSocket protocol, Zero integration, and UI updates

### Operations
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Development setup, testing, and contribution guidelines
- [API_REFERENCE.md](docs/API_REFERENCE.md) - Complete API endpoint documentation
- [OPENSEARCH_SYNC_RUNBOOK.md](docs/OPENSEARCH_SYNC_RUNBOOK.md) - Troubleshooting search sync issues

### Advanced Topics
- [CQRS_PATTERNS.md](docs/CQRS_PATTERNS.md) - CQRS implementation patterns and trade-offs
- [DYNAMIC_PRICING.md](docs/DYNAMIC_PRICING.md) - Dynamic pricing implementation and configuration
- [EXTENDING_ONTOLOGY.md](docs/EXTENDING_ONTOLOGY.md) - Step-by-step guide to adding new entity types

## Key Design Decisions

### Why RDF-Style Triples?
- Universal data model accommodates any entity type without schema migrations
- Semantic relationships preserved as first-class graph edges
- Ontology validation prevents invalid data at write time
- Easy to reason over with AI agents using SPARQL-like queries

### Why CQRS with Materialize?
- Write model (PostgreSQL) optimized for consistency and validation
- Read model (Materialize) optimized for query performance with indexes
- Independent scaling: Add read replicas without impacting write throughput
- Real-time consistency: CDC ensures views update within milliseconds

### Why OpenSearch for Agents?
- Natural language queries require full-text search capabilities
- Agents can search by partial matches, synonyms, and fuzzy text
- OpenSearch provides relevance ranking for best-match results
- Complement to structured queries over Materialize views

### Why Three-Tier Materialize Architecture?
- **Ingest cluster**: Dedicated resources for CDC replication
- **Compute cluster**: Isolated aggregation and transformation workloads
- **Serving cluster**: Indexed queries without impacting compute
- Resource isolation prevents one workload from starving others

## Security Considerations

**DoS Protection:**
- Order line creation limited to 100 products per request
- Query timeouts prevent runaway queries
- Rate limiting on API endpoints (configure via environment)

**Data Validation:**
- NULL handling with COALESCE prevents calculation failures
- Ontology validation prevents malformed triples
- Entity reference validation ensures referential integrity
- Insufficient stock errors (no silent quantity modifications)

**Observability:**
- Structured logging with query execution times
- Slow query warnings (threshold: 100ms)
- Query statistics API at `/stats` endpoint
- Health and readiness probes for monitoring

## License

MIT

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Development setup instructions
- Testing guidelines
- Code style and conventions
- Pull request process
- Community guidelines

## Support

- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: See `/docs` directory for detailed guides
- **API Reference**: Interactive Swagger UI at http://localhost:8080/docs
- **Examples**: See `db/seed/` for demo data examples
