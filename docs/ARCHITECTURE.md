# Architecture

This document explains the FreshMart Digital Twin architecture, covering the CQRS pattern, Materialize integration, and real-time data flow.

## Table of Contents

- [CQRS Pattern](#cqrs-pattern)
- [Three-Tier Architecture](#three-tier-architecture)
- [Real-Time Data Flow](#real-time-data-flow)
- [SUBSCRIBE Streaming](#subscribe-streaming)
- [System Architecture Diagram](#system-architecture-diagram)
- [Automatic Reconnection and Resilience](#automatic-reconnection--resilience)
- [Services](#services)

## CQRS Pattern

FreshMart implements **CQRS (Command Query Responsibility Segregation)** to separate write and read concerns for optimal performance and data integrity.

### Commands (Writes)

All modifications flow through the **PostgreSQL triple store** as RDF-style subject-predicate-object statements:

- Writes are validated against the **ontology schema** (classes, properties, ranges, domains)
- This ensures data integrity and semantic consistency at write time
- The triple store acts as the governed source of truth

**Write Flow:**
```
Client → FastAPI → PostgreSQL triple store → CDC → Materialize
```

### Queries (Reads)

Read operations use **Materialize materialized views** that are pre-computed, denormalized, and indexed:

- Views are maintained in real-time via **Change Data Capture (CDC)** from PostgreSQL
- Optimized for fast queries without impacting write performance
- All UI queries routed through Materialize's serving cluster

**Read Flow:**
```
Client → FastAPI → Materialize (serving cluster) → Indexed materialized views
```

### Benefits

- **Write model**: Enforces schema through ontology, maintains graph relationships
- **Read model**: Optimized for specific query patterns (orders, inventory, customer lookups)
- **Real-time consistency**: CDC ensures views reflect writes within milliseconds
- **Scalability**: Independent scaling of write (PostgreSQL) and read (Materialize) workloads

## Three-Tier Architecture

Materialize uses a **three-tier cluster architecture** for efficient data processing:

```
┌─────────────────────────────────────────────────────────────┐
│                    Ingest Cluster                            │
│  - PostgreSQL CDC source (pg_source)                         │
│  - Replicates triples table in real-time                     │
└────────────────────────┬────────────────────────────────────┘
                         │ (Change Data Capture)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Compute Cluster                            │
│  - Materialized views transform triples                      │
│  - Pre-aggregates and denormalizes data                      │
│  - Joins entities (orders + customers + stores)              │
└────────────────────────┬────────────────────────────────────┘
                         │ (Materialized results)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Serving Cluster                            │
│  - Indexes on materialized views                             │
│  - Sub-millisecond query latency                             │
│  - All application queries hit this cluster                  │
└─────────────────────────────────────────────────────────────┘
```

### Cluster Responsibilities

**Ingest Cluster**:
- Connects to PostgreSQL via CDC
- Replicates `triples` table changes in real-time
- No application queries hit this cluster

**Compute Cluster**:
- Maintains materialized views with transformation logic
- Flattens triples into entity-shaped records
- Performs joins and aggregations
- Examples: `orders_flat_mv`, `store_inventory_mv`, `customers_mv`

**Serving Cluster**:
- Hosts indexes on materialized views
- Provides low-latency lookups for applications
- All FreshMart API queries use this cluster
- Examples: `orders_search_source_idx`, `store_inventory_idx`

### Materialized Views in FreshMart

All FreshMart endpoints query precomputed, indexed materialized views:

| API Endpoint | Materialized View | Index |
|--------------|-------------------|-------|
| `/freshmart/orders` | `orders_search_source_mv` | `orders_search_source_idx` |
| `/freshmart/stores/inventory` | `store_inventory_mv` | `store_inventory_idx` |
| `/freshmart/couriers` | `courier_schedule_mv` | `courier_schedule_idx` |
| `/freshmart/stores` | `stores_mv` | `stores_idx` |
| `/freshmart/customers` | `customers_mv` | `customers_idx` |
| `/freshmart/products` | `products_mv` | `products_idx` |
| UI Order Creation | `inventory_items_with_dynamic_pricing` | `inventory_items_with_dynamic_pricing_idx` |

## Real-Time Data Flow

FreshMart achieves **sub-second latency** for data propagation across all components:

### Complete Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. WRITE: Client updates order status                               │
│     POST /triples → PostgreSQL (validated by ontology)               │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ (< 100ms)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. CDC: Change Data Capture                                         │
│     PostgreSQL → Materialize ingest cluster                          │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ (< 200ms)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  3. COMPUTE: Materialize compute cluster                             │
│     orders_flat → orders_search_source_mv (with enrichment)          │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ (< 500ms)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  4. SUBSCRIBE: Real-time streaming                                   │
│     Zero WebSocket Server subscribes to MV                           │
│     Search Sync Worker subscribes to MV                              │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ (< 100ms)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  5. BROADCAST: Push to clients                                       │
│     WebSocket → UI clients (differential updates)                    │
│     Bulk upsert → OpenSearch (for search)                            │
└──────────────────────────────────────────────────────────────────────┘

Total latency: < 1 second (write → UI update)
```

### Data Flow Paths

**UI Updates** (Real-time):
1. Write → PostgreSQL
2. CDC → Materialize
3. SUBSCRIBE → Zero server
4. WebSocket → UI clients
5. **Latency: < 1 second**

**Search Updates** (Real-time):
1. Write → PostgreSQL
2. CDC → Materialize
3. SUBSCRIBE → Search Sync Worker
4. Bulk upsert → OpenSearch
5. **Latency: < 2 seconds**

**Direct Queries** (Indexed):
1. Client → API
2. Query → Materialize serving cluster
3. Index lookup → Response
4. **Latency: < 10ms**

## SUBSCRIBE Streaming

Materialize's **SUBSCRIBE** command enables real-time streaming of differential updates from materialized views.

### How SUBSCRIBE Works

SUBSCRIBE provides a continuous stream of changes as they occur:

```sql
SUBSCRIBE (
    SELECT * FROM orders_search_source_mv
) WITH (PROGRESS);
```

**Response Format:**
```
mz_timestamp | mz_diff | order_id | order_number | ...
-------------|---------|----------|--------------|-----
1234567890   | 1       | order:1  | FM-1001      | ... (INSERT)
1234567891   | -1      | order:1  | FM-1001      | ... (DELETE)
1234567891   | 1       | order:1  | FM-1001      | ... (INSERT with new data)
```

### SUBSCRIBE Features

**Differential Updates**:
- `mz_diff = 1`: Row inserted or updated
- `mz_diff = -1`: Row deleted
- Timestamp tracks when change occurred

**PROGRESS Option**:
- Emits progress messages showing timestamps advancing
- Enables timestamp-based batching for efficient processing
- Guarantees all changes up to timestamp T have been delivered

**Snapshot Handling**:
- Initial connection emits full snapshot of current data
- Can be skipped if initial hydration already performed
- Subsequent messages are only differential updates

### FreshMart's SUBSCRIBE Usage

FreshMart uses SUBSCRIBE in two services:

**1. Zero WebSocket Server** (for UI real-time updates):
- Subscribes to multiple materialized views: `orders_flat_mv`, `stores_mv`, `courier_schedule_mv`
- Broadcasts differential updates to connected WebSocket clients
- Collections map to UI pages: orders, stores, couriers

**2. Search Sync Worker** (for OpenSearch indexing):
- Subscribes to: `orders_search_source_mv` and `store_inventory_mv`
- Consolidates DELETE + INSERT at same timestamp → UPDATE operation
- Bulk upserts to OpenSearch indexes
- Handles backpressure and automatic reconnection

### SUBSCRIBE Stream Processing

Both services follow a common pattern:

**1. Initial Hydration**:
```python
# Query current state and bulk load
results = await materialize.query("SELECT * FROM view_name")
await bulk_load_to_destination(results)
```

**2. Subscribe Connection**:
```python
# Establish SUBSCRIBE stream
async for row in materialize.subscribe(view_name):
    if is_snapshot(row):
        continue  # Skip snapshot, already hydrated
    elif is_progress(row):
        await flush_batch()  # Timestamp advanced, flush pending changes
    else:
        batch.append(row)  # Accumulate changes
```

**3. Event Consolidation** (for updates):
```python
# Track net changes per document ID
net_changes = defaultdict(lambda: {"diff": 0, "latest_data": None})

for event in batch:
    doc_id = event["id"]
    net_changes[doc_id]["diff"] += event["mz_diff"]
    net_changes[doc_id]["latest_data"] = event

# Process consolidated changes
for doc_id, change in net_changes.items():
    if change["diff"] == 1:
        upsert(doc_id, change["latest_data"])
    elif change["diff"] == -1:
        delete(doc_id)
    # diff == 0 means DELETE + INSERT = UPDATE, use latest data
```

**4. Bulk Flush**:
```python
# Bulk operations to destination
await destination.bulk_upsert(upserts)
await destination.bulk_delete(deletes)
```

### Benefits of SUBSCRIBE

- **Real-time**: Changes stream instantly (< 100ms from MV update)
- **Efficient**: Only differential updates transmitted, not full snapshots
- **Guaranteed delivery**: PROGRESS messages ensure no missed updates
- **Scalability**: Single worker handles 10,000+ events/second
- **Resource-efficient**: 50% reduction vs polling loops

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Admin UI (React)                                    │
│                      Port: 5173                                          │
│  • Real-time updates via WebSocket                                       │
│  • Orders, Couriers, Stores/Inventory dashboards                         │
└──────────────┬──────────────────────────────────┬────────────────────────┘
               │ REST API (writes/reads)          ▲ WebSocket (real-time)
               ▼                                  │
┌──────────────────────────┐         ┌─────────────────────────────────────┐
│  Graph/Ontology API      │         │    Zero WebSocket Server            │
│  (FastAPI) Port: 8080    │         │    Port: 8090                       │
│  • Ontology CRUD         │         │  • SUBSCRIBE to Materialize MVs     │
│  • Triple CRUD           │         │  • Broadcast changes to clients     │
│  • FreshMart endpoints   │         │  • Collections: orders, stores,     │
│  • Query logging         │         │    couriers, inventory              │
└───────┬──────────────────┘         └────────────▲────────────────────────┘
        │ writes                                  │ SUBSCRIBE
        ▼                                         │ (differential updates)
┌──────────────────────────┐         ┌───────────┴─────────────────────────┐
│     PostgreSQL           │         │      Materialize                     │
│     Port: 5432           │────────▶│  Console: 6874 SQL: 6875             │
│  • ontology_classes      │ (CDC)   │  Three-Tier Architecture:            │
│  • ontology_properties   │         │  • ingest: pg_source (CDC)           │
│  • triples               │         │  • compute: MVs (aggregation)        │
└──────────────────────────┘         │  • serving: indexes (queries)        │
                                     │  SUBSCRIBE: differential updates     │
                                     └────────────┬────────────────────────┘
                                                  │ SUBSCRIBE
                                                  │ (real-time streaming)
                                     ┌────────────▼────────────────────────┐
                                     │    Search Sync Worker                │
                                     │  SUBSCRIBE streaming                 │
                                     │  • OrdersSyncWorker (orders)         │
                                     │  • InventorySyncWorker (inventory)   │
                                     │  • BaseSubscribeWorker pattern       │
                                     │  • Event consolidation               │
                                     │  • < 2s latency                      │
                                     └────────────┬────────────────────────┘
                                                  │ Bulk index
                                                  ▼
                    ┌─────────────────────────────────────┐
                    │      OpenSearch                     │
           ┌───────▶│       Port: 9200                    │
           │        │  • orders index (real-time)         │
           │        │  • inventory index (real-time)      │
           │        │  • Full-text search                 │
           │        └─────────────────────────────────────┘
           │
┌──────────┴───────────────┐
│    LangGraph Agents       │
│      Port: 8081           │
│  • search_orders  ────────┘ (search orders index)
│  • search_inventory ─────┘ (search inventory index)
│  • fetch_order_context ─────▶ Graph API (read triples)
│  • write_triples ───────────▶ Graph API (write triples → PostgreSQL)
└──────────────────────────┘
```

## Automatic Reconnection & Resilience

Both `zero-server` and `search-sync` services include automatic retry and reconnection logic for production reliability.

### Connection Retry

Services start even if Materialize is not ready:

- Automatically retry connection every 30 seconds until successful
- No manual intervention needed when Materialize is initializing
- Services log retry attempts for monitoring

**Startup sequence:**
```
[zero-server] Attempting connection to Materialize... (attempt 1)
[zero-server] Connection refused, retrying in 30s
[zero-server] Attempting connection to Materialize... (attempt 2)
[zero-server] Connected successfully!
```

### Stream Reconnection

If a SUBSCRIBE stream ends or errors, services automatically reconnect:

- Handles network interruptions and Materialize restarts gracefully
- Each view maintains its own reconnection loop independently
- Re-establishes SUBSCRIBE without data loss

**Reconnection flow:**
```
[orders_flat_mv] SUBSCRIBE stream ended (connection lost)
[orders_flat_mv] Retrying connection... (attempt 1)
[orders_flat_mv] Re-hydrating from current state...
[orders_flat_mv] SUBSCRIBE stream re-established
```

### Configuration

**zero-server**: Fixed 30-second retry delay per subscription

**search-sync**: Exponential backoff for efficiency
- Initial delay: 1 second
- Backoff multiplier: 2x
- Maximum delay: 30 seconds
- Sequence: 1s → 2s → 4s → 8s → 16s → 30s (cap)

Environment variables (search-sync):
```bash
RETRY_INITIAL_DELAY=1       # Initial retry delay (seconds)
RETRY_MAX_DELAY=30          # Maximum retry delay (seconds)
RETRY_BACKOFF_MULTIPLIER=2  # Backoff multiplier
```

### Benefits

- **Start services in any order** - they'll connect when ready
- **No manual restarts** - if Materialize restarts, services automatically reconnect
- **Continuous real-time updates** - even after connection issues
- **Production-ready** - handles network interruptions gracefully

## Services

| Service | Port | Description |
|---------|------|-------------|
| **db** | 5432 | PostgreSQL - primary triple store |
| **mz** | 6874 | Materialize Admin Console |
| **mz** | 6875 | Materialize SQL interface |
| **zero-server** | 8090 | WebSocket server for real-time UI updates |
| **opensearch** | 9200 | Search engine for orders |
| **api** | 8080 | FastAPI backend |
| **search-sync** | - | Dual SUBSCRIBE workers (orders + inventory) for OpenSearch sync (< 2s latency) |
| **web** | 5173 | React admin UI with real-time updates |
| **agents** | 8081 | LangGraph agent runner (optional) |

## See Also

- [Operations Guide](OPERATIONS.md) - Service management and troubleshooting
- [Ontology Guide](ONTOLOGY_GUIDE.md) - Adding new entity types and views
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [UI Guide](UI_GUIDE.md) - Dashboard features and real-time UI
- [Agents Guide](AGENTS.md) - AI agent setup and usage
