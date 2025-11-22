-- Materialize Initialization Script
-- Creates PostgreSQL source connection and materialized views

-- =============================================================================
-- Create a connection to PostgreSQL (main database)
-- =============================================================================
CREATE SECRET IF NOT EXISTS pgpass AS 'postgres';

CREATE CONNECTION IF NOT EXISTS pg_connection TO POSTGRES (
    HOST 'db',
    PORT 5432,
    USER 'postgres',
    PASSWORD SECRET pgpass,
    DATABASE 'freshmart'
);

-- =============================================================================
-- Create a source from PostgreSQL triples table
-- =============================================================================
CREATE SOURCE IF NOT EXISTS triples_source
FROM POSTGRES CONNECTION pg_connection (PUBLICATION 'mz_source')
FOR TABLES (triples);

-- =============================================================================
-- Orders Flattened View
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS orders_flat_mz AS
SELECT
    subject_id AS order_id,
    MAX(CASE WHEN predicate = 'order_number' THEN object_value END) AS order_number,
    MAX(CASE WHEN predicate = 'order_status' THEN object_value END) AS order_status,
    MAX(CASE WHEN predicate = 'order_store' THEN object_value END) AS store_id,
    MAX(CASE WHEN predicate = 'placed_by' THEN object_value END) AS customer_id,
    MAX(CASE WHEN predicate = 'delivery_window_start' THEN object_value END) AS delivery_window_start,
    MAX(CASE WHEN predicate = 'delivery_window_end' THEN object_value END) AS delivery_window_end,
    MAX(CASE WHEN predicate = 'order_total_amount' THEN object_value END)::DECIMAL(10,2) AS order_total_amount,
    MAX(updated_at) AS effective_updated_at
FROM triples
WHERE subject_id LIKE 'order:%'
GROUP BY subject_id;

-- =============================================================================
-- Store Inventory View
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS store_inventory_mz AS
SELECT
    subject_id AS inventory_id,
    MAX(CASE WHEN predicate = 'inventory_store' THEN object_value END) AS store_id,
    MAX(CASE WHEN predicate = 'inventory_product' THEN object_value END) AS product_id,
    MAX(CASE WHEN predicate = 'stock_level' THEN object_value END)::INT AS stock_level,
    MAX(CASE WHEN predicate = 'replenishment_eta' THEN object_value END) AS replenishment_eta,
    MAX(updated_at) AS effective_updated_at
FROM triples
WHERE subject_id LIKE 'inventory:%'
GROUP BY subject_id;

-- =============================================================================
-- Orders Search Source View (for OpenSearch sync)
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS orders_search_source AS
SELECT
    o.order_id,
    o.order_number,
    o.order_status,
    o.store_id,
    o.customer_id,
    o.delivery_window_start,
    o.delivery_window_end,
    o.order_total_amount,
    -- Customer details (from separate query)
    c.customer_name,
    c.customer_email,
    c.customer_address,
    -- Store details
    s.store_name,
    s.store_zone,
    s.store_address,
    -- Delivery task info
    dt.assigned_courier_id,
    dt.task_status AS delivery_task_status,
    dt.eta AS delivery_eta,
    -- Timestamp for incremental sync
    GREATEST(
        o.effective_updated_at,
        c.effective_updated_at,
        s.effective_updated_at,
        dt.effective_updated_at
    ) AS effective_updated_at
FROM orders_flat_mz o
LEFT JOIN (
    SELECT
        subject_id AS customer_id,
        MAX(CASE WHEN predicate = 'customer_name' THEN object_value END) AS customer_name,
        MAX(CASE WHEN predicate = 'customer_email' THEN object_value END) AS customer_email,
        MAX(CASE WHEN predicate = 'customer_address' THEN object_value END) AS customer_address,
        MAX(updated_at) AS effective_updated_at
    FROM triples
    WHERE subject_id LIKE 'customer:%'
    GROUP BY subject_id
) c ON c.customer_id = o.customer_id
LEFT JOIN (
    SELECT
        subject_id AS store_id,
        MAX(CASE WHEN predicate = 'store_name' THEN object_value END) AS store_name,
        MAX(CASE WHEN predicate = 'store_zone' THEN object_value END) AS store_zone,
        MAX(CASE WHEN predicate = 'store_address' THEN object_value END) AS store_address,
        MAX(updated_at) AS effective_updated_at
    FROM triples
    WHERE subject_id LIKE 'store:%'
    GROUP BY subject_id
) s ON s.store_id = o.store_id
LEFT JOIN (
    SELECT
        MAX(CASE WHEN predicate = 'task_of_order' THEN object_value END) AS order_id,
        MAX(CASE WHEN predicate = 'assigned_to' THEN object_value END) AS assigned_courier_id,
        MAX(CASE WHEN predicate = 'task_status' THEN object_value END) AS task_status,
        MAX(CASE WHEN predicate = 'eta' THEN object_value END) AS eta,
        MAX(updated_at) AS effective_updated_at
    FROM triples
    WHERE subject_id LIKE 'task:%'
    GROUP BY subject_id
) dt ON dt.order_id = o.order_id;
