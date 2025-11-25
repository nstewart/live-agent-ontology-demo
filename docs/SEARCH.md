# Search Integration

This document describes the OpenSearch integration for full-text search capabilities.

## Overview

OpenSearch provides:
- Full-text search across orders
- Fuzzy matching for typos
- Multi-field search (customer name, address, order number)
- Fast retrieval for the agent's search tools

## Index Schema

### Orders Index

```json
{
  "mappings": {
    "properties": {
      "order_id": { "type": "keyword" },
      "order_number": { "type": "keyword", "copy_to": "search_text" },
      "order_status": { "type": "keyword" },
      "store_id": { "type": "keyword" },
      "customer_id": { "type": "keyword" },
      "delivery_window_start": { "type": "date" },
      "delivery_window_end": { "type": "date" },
      "order_total_amount": { "type": "float" },
      "customer_name": {
        "type": "text",
        "copy_to": "search_text",
        "fields": { "keyword": { "type": "keyword" }}
      },
      "customer_email": { "type": "keyword" },
      "customer_address": {
        "type": "text",
        "copy_to": "search_text",
        "fields": { "keyword": { "type": "keyword" }}
      },
      "store_name": {
        "type": "text",
        "copy_to": "search_text",
        "fields": { "keyword": { "type": "keyword" }}
      },
      "store_zone": { "type": "keyword" },
      "assigned_courier_id": { "type": "keyword" },
      "delivery_task_status": { "type": "keyword" },
      "delivery_eta": { "type": "date" },
      "effective_updated_at": { "type": "date" },
      "search_text": { "type": "text" }
    }
  }
}
```

## Sync Worker

The `search-sync` service polls Materialize and syncs to OpenSearch.

### Sync Flow

1. **Poll Materialize**: Query `orders_search_source` for rows updated since last sync
2. **Transform**: Convert to OpenSearch document format
3. **Bulk Upsert**: Use OpenSearch bulk API for efficient indexing
4. **Update Cursor**: Track last synced timestamp

### Configuration

```bash
# Environment variables
POLL_INTERVAL=5          # Seconds between polls
BATCH_SIZE=100           # Documents per batch
```

### Example Sync

```python
# Query for changed documents
SELECT * FROM orders_search_source
WHERE effective_updated_at > :last_cursor
ORDER BY effective_updated_at
LIMIT :batch_size

# Bulk upsert to OpenSearch
POST /_bulk
{"index": {"_index": "orders", "_id": "order:FM-1001"}}
{"order_id": "order:FM-1001", "order_number": "FM-1001", ...}
```

## Search Queries

### Basic Search

```bash
# Search via OpenSearch directly
POST /orders/_search
{
  "query": {
    "multi_match": {
      "query": "Alex Thompson",
      "fields": ["customer_name^2", "customer_address", "order_number^3"],
      "type": "best_fields",
      "fuzziness": "AUTO"
    }
  }
}
```

### Filtered Search

```bash
# Search with status filter
POST /orders/_search
{
  "query": {
    "bool": {
      "must": [
        {"multi_match": {"query": "Brooklyn", "fields": ["search_text"]}}
      ],
      "filter": [
        {"term": {"order_status": "OUT_FOR_DELIVERY"}}
      ]
    }
  }
}
```

### Via Agent Tool

The agent's `search_orders` tool wraps OpenSearch:

```python
results = await search_orders(
    query="Alex Thompson",
    status="OUT_FOR_DELIVERY",
    limit=10
)
```

## Extending Search

### Adding New Indices

1. **Define mapping** in `opensearch_client.py`
2. **Create sync view** in Materialize
3. **Add sync logic** to worker
4. **Create agent tool** for querying

### Example: Store Search

```python
# Add to opensearch_client.py
STORES_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "store_id": {"type": "keyword"},
            "store_name": {"type": "text"},
            "store_address": {"type": "text"},
            "store_zone": {"type": "keyword"},
            "store_status": {"type": "keyword"}
        }
    }
}

# Add sync logic in orders_sync.py or new file
async def sync_stores():
    # Similar pattern to orders sync
    pass
```

## Monitoring

### Check Index Health

```bash
# Get index stats
curl http://localhost:9200/orders/_stats

# Check cluster health
curl http://localhost:9200/_cluster/health
```

### Debug Sync Issues

```bash
# Check sync cursor
docker-compose exec mz psql -U materialize -d materialize -c \
  "SELECT * FROM sync_cursors"

# Check worker logs
docker-compose logs -f search-sync
```

## Performance Tips

1. **Batch Size**: Adjust `BATCH_SIZE` based on document size
2. **Poll Interval**: Balance freshness vs. load with `POLL_INTERVAL`
3. **Index Settings**: Single shard/replica for dev, scale for production
4. **Refresh Interval**: OpenSearch defaults to 1s refresh
