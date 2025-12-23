-- 082_orders_with_lines_batch.sql
-- Migration: Create enhanced orders_with_lines view and batch MATERIALIZED VIEW
-- for Query Statistics comparison between PostgreSQL VIEW, Batch Cache, and Materialize

-- =============================================================================
-- Enhanced orders_with_lines view with customer, store, and delivery task info
-- This VIEW computes on every query (fresh but potentially slower)
-- =============================================================================
CREATE OR REPLACE VIEW orders_with_lines_full AS
SELECT
    o.order_id,
    o.order_number,
    o.order_status,
    o.store_id,
    o.customer_id,
    o.delivery_window_start,
    o.delivery_window_end,
    o.order_total_amount,
    -- Customer fields
    c.customer_name,
    c.customer_email,
    c.customer_address,
    -- Store fields
    s.store_name,
    s.store_zone,
    s.store_address,
    -- Delivery task fields (from courier_schedule_flat tasks)
    dt.task_id AS delivery_task_id,
    dt.assigned_courier_id,
    dt.task_status AS delivery_task_status,
    dt.eta AS delivery_eta,
    -- Line items as JSONB
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'line_id', ol.line_id,
                'product_id', ol.product_id,
                'product_name', ol.product_name,
                'category', ol.category,
                'quantity', ol.quantity,
                'unit_price', ol.unit_price,
                'line_amount', ol.line_amount,
                'line_sequence', ol.line_sequence,
                'perishable_flag', ol.perishable_flag
            ) ORDER BY ol.line_sequence
        ) FILTER (WHERE ol.line_id IS NOT NULL),
        '[]'::jsonb
    ) AS line_items,
    COUNT(ol.line_id) AS line_item_count,
    SUM(ol.line_amount) AS computed_total,
    BOOL_OR(ol.perishable_flag) AS has_perishable_items,
    -- Effective updated_at is the MAX of all related entity timestamps
    GREATEST(
        o.effective_updated_at,
        MAX(ol.effective_updated_at),
        c.effective_updated_at,
        s.effective_updated_at
    ) AS effective_updated_at
FROM orders_flat o
LEFT JOIN customers_flat c ON c.customer_id = o.customer_id
LEFT JOIN stores_flat s ON s.store_id = o.store_id
LEFT JOIN order_lines_flat ol ON ol.order_id = o.order_id
LEFT JOIN LATERAL (
    -- Get the delivery task for this order from the triples
    SELECT
        t_task.subject_id AS task_id,
        MAX(CASE WHEN t2.predicate = 'assigned_to' THEN t2.object_value END) AS assigned_courier_id,
        MAX(CASE WHEN t2.predicate = 'task_status' THEN t2.object_value END) AS task_status,
        MAX(CASE WHEN t2.predicate = 'eta' THEN t2.object_value END) AS eta
    FROM triples t_task
    LEFT JOIN triples t2 ON t2.subject_id = t_task.subject_id
    WHERE t_task.predicate = 'task_of_order'
      AND t_task.object_value = o.order_id
    GROUP BY t_task.subject_id
    LIMIT 1
) dt ON true
GROUP BY
    o.order_id,
    o.order_number,
    o.order_status,
    o.store_id,
    o.customer_id,
    o.delivery_window_start,
    o.delivery_window_end,
    o.order_total_amount,
    o.effective_updated_at,
    c.customer_name,
    c.customer_email,
    c.customer_address,
    c.effective_updated_at,
    s.store_name,
    s.store_zone,
    s.store_address,
    s.effective_updated_at,
    dt.task_id,
    dt.assigned_courier_id,
    dt.task_status,
    dt.eta;

-- =============================================================================
-- Batch MATERIALIZED VIEW for orders_with_lines
-- This is pre-computed and refreshed every 60 seconds (fast but stale)
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS orders_with_lines_batch AS
SELECT * FROM orders_with_lines_full;

-- Index for efficient order lookup on the batch materialized view
CREATE INDEX IF NOT EXISTS orders_with_lines_batch_order_id_idx
ON orders_with_lines_batch (order_id);

-- Index for ordering by effective_updated_at
CREATE INDEX IF NOT EXISTS orders_with_lines_batch_updated_idx
ON orders_with_lines_batch (effective_updated_at DESC);

-- Add refresh log entry for tracking
INSERT INTO materialized_view_refresh_log (view_name, last_refresh)
VALUES ('orders_with_lines_batch', NOW())
ON CONFLICT (view_name) DO NOTHING;

-- Add comments
COMMENT ON VIEW orders_with_lines_full IS 'Enhanced orders with lines, customer, store, and delivery info. Computes on every query (fresh but slower).';
COMMENT ON MATERIALIZED VIEW orders_with_lines_batch IS 'Pre-computed batch cache of orders_with_lines_full. Refreshed every 60 seconds (fast but stale).';

-- Insert migration record
INSERT INTO schema_migrations (version) VALUES ('082_orders_with_lines_batch')
ON CONFLICT (version) DO NOTHING;
