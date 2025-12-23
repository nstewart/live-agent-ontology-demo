-- Query Statistics Tables
-- Used for measuring and comparing query response time and reaction time
-- across different data access patterns (PostgreSQL View, Batch Cache, Materialize)

-- Heartbeats table for measuring Materialize replication lag
CREATE TABLE IF NOT EXISTS heartbeats (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient latest heartbeat lookup
CREATE INDEX IF NOT EXISTS heartbeats_idx ON heartbeats (id DESC);

-- Set replica identity for heartbeats table (required for Materialize logical replication)
ALTER TABLE heartbeats REPLICA IDENTITY FULL;

-- Batch cache materialized view for orders
-- This is the same SQL as orders_flat but as a MATERIALIZED VIEW
-- It is refreshed every 60 seconds to simulate batch/ETL processing
-- The effective_updated_at is frozen at refresh time, demonstrating staleness
CREATE MATERIALIZED VIEW IF NOT EXISTS orders_flat_batch AS
WITH order_subjects AS (
    SELECT DISTINCT subject_id
    FROM triples
    WHERE subject_id LIKE 'order:%'
)
SELECT
    os.subject_id AS order_id,
    MAX(CASE WHEN t.predicate = 'order_number' THEN t.object_value END) AS order_number,
    MAX(CASE WHEN t.predicate = 'order_status' THEN t.object_value END) AS order_status,
    MAX(CASE WHEN t.predicate = 'order_store' THEN t.object_value END) AS store_id,
    MAX(CASE WHEN t.predicate = 'placed_by' THEN t.object_value END) AS customer_id,
    MAX(CASE WHEN t.predicate = 'delivery_window_start' THEN t.object_value END) AS delivery_window_start,
    MAX(CASE WHEN t.predicate = 'delivery_window_end' THEN t.object_value END) AS delivery_window_end,
    MAX(CASE WHEN t.predicate = 'order_total_amount' THEN t.object_value END)::DECIMAL(10,2) AS order_total_amount,
    MAX(t.updated_at) AS effective_updated_at
FROM order_subjects os
LEFT JOIN triples t ON t.subject_id = os.subject_id
GROUP BY os.subject_id;

-- Index for efficient order lookup on the batch materialized view
CREATE INDEX IF NOT EXISTS orders_flat_batch_order_id_idx ON orders_flat_batch (order_id);

-- Table to track materialized view refresh times
CREATE TABLE IF NOT EXISTS materialized_view_refresh_log (
    view_name TEXT PRIMARY KEY,
    last_refresh TIMESTAMPTZ DEFAULT NOW(),
    refresh_duration_ms DOUBLE PRECISION DEFAULT 0
);

-- Insert initial record for orders_flat_batch
INSERT INTO materialized_view_refresh_log (view_name, last_refresh)
VALUES ('orders_flat_batch', NOW())
ON CONFLICT (view_name) DO NOTHING;
