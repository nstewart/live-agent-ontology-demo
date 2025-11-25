-- Materialize Emulator Initialization
-- Uses PostgreSQL with materialized views to emulate Materialize behavior

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE EXTENSION IF NOT EXISTS dblink;

-- =============================================================================
-- Foreign Data Wrapper to connect to main database
-- =============================================================================
-- Note: In production, you would use real Materialize with its Postgres source

CREATE SERVER IF NOT EXISTS main_db
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'db', port '5432', dbname 'freshmart');

CREATE USER MAPPING IF NOT EXISTS FOR materialize
    SERVER main_db
    OPTIONS (user 'postgres', password 'postgres');

-- Import the triples table from main database
DROP FOREIGN TABLE IF EXISTS triples_source CASCADE;
CREATE FOREIGN TABLE triples_source (
    id BIGINT,
    subject_id TEXT,
    predicate TEXT,
    object_value TEXT,
    object_type TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
SERVER main_db
OPTIONS (schema_name 'public', table_name 'triples');

-- =============================================================================
-- Local copy of triples for materialized views
-- =============================================================================
CREATE TABLE IF NOT EXISTS triples_mz (
    id BIGINT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_value TEXT NOT NULL,
    object_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_triples_mz_subject ON triples_mz(subject_id);
CREATE INDEX IF NOT EXISTS idx_triples_mz_predicate ON triples_mz(predicate);
CREATE INDEX IF NOT EXISTS idx_triples_mz_subject_predicate ON triples_mz(subject_id, predicate);
CREATE INDEX IF NOT EXISTS idx_triples_mz_updated ON triples_mz(updated_at);

-- =============================================================================
-- Refresh function to sync triples from main database
-- =============================================================================
CREATE OR REPLACE FUNCTION refresh_triples_mz()
RETURNS void AS $$
BEGIN
    -- Upsert changed/new rows
    INSERT INTO triples_mz (id, subject_id, predicate, object_value, object_type, created_at, updated_at)
    SELECT id, subject_id, predicate, object_value, object_type, created_at, updated_at
    FROM triples_source
    ON CONFLICT (id) DO UPDATE SET
        subject_id = EXCLUDED.subject_id,
        predicate = EXCLUDED.predicate,
        object_value = EXCLUDED.object_value,
        object_type = EXCLUDED.object_type,
        updated_at = EXCLUDED.updated_at;

    -- Remove deleted rows
    DELETE FROM triples_mz
    WHERE id NOT IN (SELECT id FROM triples_source);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Orders Flattened Materialized View
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS orders_flat_mz AS
WITH order_subjects AS (
    SELECT DISTINCT subject_id
    FROM triples_mz
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
LEFT JOIN triples_mz t ON t.subject_id = os.subject_id
GROUP BY os.subject_id;

CREATE UNIQUE INDEX IF NOT EXISTS orders_flat_mz_pk ON orders_flat_mz(order_id);

-- =============================================================================
-- Store Inventory Materialized View
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS store_inventory_mz AS
WITH inventory_subjects AS (
    SELECT DISTINCT subject_id
    FROM triples_mz
    WHERE subject_id LIKE 'inventory:%'
)
SELECT
    inv.subject_id AS inventory_id,
    MAX(CASE WHEN t.predicate = 'inventory_store' THEN t.object_value END) AS store_id,
    MAX(CASE WHEN t.predicate = 'inventory_product' THEN t.object_value END) AS product_id,
    MAX(CASE WHEN t.predicate = 'stock_level' THEN t.object_value END)::INT AS stock_level,
    MAX(CASE WHEN t.predicate = 'replenishment_eta' THEN t.object_value END) AS replenishment_eta,
    MAX(t.updated_at) AS effective_updated_at
FROM inventory_subjects inv
LEFT JOIN triples_mz t ON t.subject_id = inv.subject_id
GROUP BY inv.subject_id;

CREATE UNIQUE INDEX IF NOT EXISTS store_inventory_mz_pk ON store_inventory_mz(inventory_id);

-- =============================================================================
-- Courier Schedule Materialized View
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS courier_schedule_mz AS
WITH courier_subjects AS (
    SELECT DISTINCT subject_id
    FROM triples_mz
    WHERE subject_id LIKE 'courier:%'
),
courier_tasks AS (
    SELECT
        t_assigned.object_value AS courier_id,
        t_task.subject_id AS task_id,
        MAX(CASE WHEN t2.predicate = 'task_status' THEN t2.object_value END) AS task_status,
        MAX(CASE WHEN t2.predicate = 'task_of_order' THEN t2.object_value END) AS order_id,
        MAX(CASE WHEN t2.predicate = 'eta' THEN t2.object_value END) AS eta,
        MAX(CASE WHEN t2.predicate = 'route_sequence' THEN t2.object_value END)::INT AS route_sequence
    FROM triples_mz t_assigned
    JOIN triples_mz t_task ON t_task.subject_id = t_assigned.subject_id
    LEFT JOIN triples_mz t2 ON t2.subject_id = t_assigned.subject_id
    WHERE t_assigned.predicate = 'assigned_to'
        AND t_assigned.object_type = 'entity_ref'
    GROUP BY t_assigned.object_value, t_task.subject_id
)
SELECT
    cs.subject_id AS courier_id,
    MAX(CASE WHEN t.predicate = 'courier_name' THEN t.object_value END) AS courier_name,
    MAX(CASE WHEN t.predicate = 'courier_home_store' THEN t.object_value END) AS home_store_id,
    MAX(CASE WHEN t.predicate = 'vehicle_type' THEN t.object_value END) AS vehicle_type,
    MAX(CASE WHEN t.predicate = 'courier_status' THEN t.object_value END) AS courier_status,
    COALESCE(
        json_agg(
            json_build_object(
                'task_id', ct.task_id,
                'task_status', ct.task_status,
                'order_id', ct.order_id,
                'eta', ct.eta,
                'route_sequence', ct.route_sequence
            )
        ) FILTER (WHERE ct.task_id IS NOT NULL),
        '[]'::json
    ) AS tasks,
    MAX(t.updated_at) AS effective_updated_at
FROM courier_subjects cs
LEFT JOIN triples_mz t ON t.subject_id = cs.subject_id
LEFT JOIN courier_tasks ct ON ct.courier_id = cs.subject_id
GROUP BY cs.subject_id;

CREATE UNIQUE INDEX IF NOT EXISTS courier_schedule_mz_pk ON courier_schedule_mz(courier_id);

-- =============================================================================
-- Orders Search Source View (for OpenSearch sync)
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS orders_search_source AS
SELECT
    ofm.order_id,
    ofm.order_number,
    ofm.order_status,
    ofm.store_id,
    ofm.customer_id,
    ofm.delivery_window_start,
    ofm.delivery_window_end,
    ofm.order_total_amount,
    -- Customer details
    MAX(CASE WHEN c.predicate = 'customer_name' THEN c.object_value END) AS customer_name,
    MAX(CASE WHEN c.predicate = 'customer_email' THEN c.object_value END) AS customer_email,
    MAX(CASE WHEN c.predicate = 'customer_address' THEN c.object_value END) AS customer_address,
    -- Store details
    MAX(CASE WHEN s.predicate = 'store_name' THEN s.object_value END) AS store_name,
    MAX(CASE WHEN s.predicate = 'store_zone' THEN s.object_value END) AS store_zone,
    MAX(CASE WHEN s.predicate = 'store_address' THEN s.object_value END) AS store_address,
    -- Delivery task info
    MAX(CASE WHEN dt.predicate = 'assigned_to' THEN dt.object_value END) AS assigned_courier_id,
    MAX(CASE WHEN dt.predicate = 'task_status' THEN dt.object_value END) AS delivery_task_status,
    MAX(CASE WHEN dt.predicate = 'eta' THEN dt.object_value END) AS delivery_eta,
    -- Timestamp for incremental sync
    GREATEST(
        ofm.effective_updated_at,
        MAX(c.updated_at),
        MAX(s.updated_at),
        MAX(dt.updated_at)
    ) AS effective_updated_at
FROM orders_flat_mz ofm
LEFT JOIN triples_mz c ON c.subject_id = ofm.customer_id
LEFT JOIN triples_mz s ON s.subject_id = ofm.store_id
LEFT JOIN triples_mz dt_ref ON dt_ref.predicate = 'task_of_order' AND dt_ref.object_value = ofm.order_id
LEFT JOIN triples_mz dt ON dt.subject_id = dt_ref.subject_id
GROUP BY
    ofm.order_id,
    ofm.order_number,
    ofm.order_status,
    ofm.store_id,
    ofm.customer_id,
    ofm.delivery_window_start,
    ofm.delivery_window_end,
    ofm.order_total_amount,
    ofm.effective_updated_at;

CREATE UNIQUE INDEX IF NOT EXISTS orders_search_source_pk ON orders_search_source(order_id);

-- =============================================================================
-- Master refresh function
-- =============================================================================
CREATE OR REPLACE FUNCTION refresh_all_views()
RETURNS void AS $$
BEGIN
    -- First sync triples from source
    PERFORM refresh_triples_mz();

    -- Then refresh materialized views
    REFRESH MATERIALIZED VIEW CONCURRENTLY orders_flat_mz;
    REFRESH MATERIALIZED VIEW CONCURRENTLY store_inventory_mz;
    REFRESH MATERIALIZED VIEW CONCURRENTLY courier_schedule_mz;
    REFRESH MATERIALIZED VIEW CONCURRENTLY orders_search_source;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Sync cursor tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS sync_cursors (
    view_name TEXT PRIMARY KEY,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01'::TIMESTAMPTZ,
    last_synced_id TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO sync_cursors (view_name) VALUES ('orders_search_source')
ON CONFLICT (view_name) DO NOTHING;
