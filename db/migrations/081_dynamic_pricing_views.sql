-- 081_dynamic_pricing_views.sql
-- Dynamic Pricing Views for Query Statistics Comparison
-- Creates the same complex view in PostgreSQL for comparing:
-- 1. PostgreSQL VIEW (computed on-demand, slow but fresh)
-- 2. PostgreSQL MATERIALIZED VIEW (pre-computed, fast but stale)
-- 3. Materialize VIEW (incrementally maintained, fast AND fresh)

-- =============================================================================
-- Step 1: Create enriched store_inventory view (mirrors Materialize store_inventory_mv)
-- =============================================================================
CREATE OR REPLACE VIEW store_inventory AS
WITH order_reservations AS (
    -- Calculate reserved quantity per product per store from pending orders
    SELECT
        o.store_id,
        ol.product_id,
        SUM(ol.quantity) AS reserved_quantity
    FROM order_lines_flat ol
    JOIN orders_flat o ON o.order_id = ol.order_id
    WHERE o.order_status IN ('CREATED', 'PICKING', 'OUT_FOR_DELIVERY')
    GROUP BY o.store_id, ol.product_id
)
SELECT
    inv.inventory_id,
    inv.store_id,
    inv.product_id,
    inv.stock_level,
    -- Reserved quantity from pending orders
    COALESCE(res.reserved_quantity, 0)::INT AS reserved_quantity,
    -- Available quantity (stock minus reservations)
    GREATEST(inv.stock_level - COALESCE(res.reserved_quantity, 0), 0)::INT AS available_quantity,
    inv.replenishment_eta,
    inv.effective_updated_at,
    -- Product details
    p.product_name,
    p.category,
    p.unit_price,
    p.perishable,
    -- Store details
    s.store_name,
    s.store_zone,
    s.store_address,
    -- Availability flags (based on AVAILABLE quantity, not total stock)
    CASE
        WHEN GREATEST(inv.stock_level - COALESCE(res.reserved_quantity, 0), 0) > 10 THEN 'IN_STOCK'
        WHEN GREATEST(inv.stock_level - COALESCE(res.reserved_quantity, 0), 0) > 0 THEN 'LOW_STOCK'
        ELSE 'OUT_OF_STOCK'
    END AS availability_status,
    (GREATEST(inv.stock_level - COALESCE(res.reserved_quantity, 0), 0) <= 10
     AND GREATEST(inv.stock_level - COALESCE(res.reserved_quantity, 0), 0) > 0) AS low_stock
FROM store_inventory_flat inv
LEFT JOIN products_flat p ON p.product_id = inv.product_id
LEFT JOIN stores_flat s ON s.store_id = inv.store_id
LEFT JOIN order_reservations res ON res.store_id = inv.store_id AND res.product_id = inv.product_id;

-- =============================================================================
-- Step 2: Create dynamic pricing VIEW (computed on-demand - SLOW but FRESH)
-- This complex view has 8 pricing factors including market basket analysis
-- Note: Time-of-day pricing excluded to match Materialize (mz_now limitation)
-- =============================================================================
CREATE OR REPLACE VIEW inventory_items_with_dynamic_pricing AS
WITH
  -- Get order lines from delivered orders with timestamps
  delivered_order_lines AS (
    SELECT
      ol.line_id,
      ol.order_id,
      ol.product_id,
      ol.category,
      ol.unit_price,
      ol.quantity,
      ol.perishable_flag,
      o.order_status,
      o.delivery_window_start,
      ol.effective_updated_at
    FROM order_lines_flat ol
    JOIN orders_flat o ON o.order_id = ol.order_id
    WHERE o.order_status = 'DELIVERED'
  ),

  -- ==========================================================================
  -- MARKET BASKET ANALYSIS (Expensive O(n²) self-join)
  -- Find products frequently bought together to enable anchor pricing strategy
  -- ==========================================================================
  product_pairs AS (
    -- Self-join order lines to find co-purchased products (expensive!)
    SELECT
      ol1.product_id AS product_a,
      ol2.product_id AS product_b,
      ol1.order_id
    FROM order_lines_flat ol1
    JOIN order_lines_flat ol2
      ON ol1.order_id = ol2.order_id
      AND ol1.product_id < ol2.product_id  -- Avoid duplicates and self-pairs
  ),

  cross_sell_affinity AS (
    -- Calculate affinity scores for each product pair
    SELECT
      product_a,
      product_b,
      COUNT(*) AS co_purchase_count,
      -- Affinity score: how often these products appear together
      COUNT(*)::numeric / NULLIF(
        (SELECT COUNT(DISTINCT order_id) FROM order_lines_flat WHERE product_id = product_a), 0
      ) AS affinity_score_a,
      COUNT(*)::numeric / NULLIF(
        (SELECT COUNT(DISTINCT order_id) FROM order_lines_flat WHERE product_id = product_b), 0
      ) AS affinity_score_b
    FROM product_pairs
    GROUP BY product_a, product_b
    HAVING COUNT(*) >= 2  -- Only consider pairs bought together at least twice
  ),

  -- Aggregate basket metrics per product (is this product a "basket driver"?)
  basket_metrics AS (
    SELECT
      product_id,
      COUNT(*) AS num_affinity_products,
      AVG(affinity_score) AS avg_affinity_score,
      MAX(co_purchase_count) AS max_copurchase_count,
      -- Products with high affinity to many others are "basket drivers"
      CASE
        WHEN COUNT(*) >= 5 AND AVG(affinity_score) > 0.3 THEN TRUE
        ELSE FALSE
      END AS is_basket_driver
    FROM (
      SELECT product_a AS product_id, affinity_score_a AS affinity_score, co_purchase_count
      FROM cross_sell_affinity
      UNION ALL
      SELECT product_b AS product_id, affinity_score_b AS affinity_score, co_purchase_count
      FROM cross_sell_affinity
    ) all_affinities
    GROUP BY product_id
  ),

  -- Note: TIME-OF-DAY DEMAND PATTERNS excluded to match Materialize
  -- (mz_now() can only be used in WHERE/HAVING, not for extracting hour values)

  -- Sales velocity: Compare recent sales (last 5 orders) to prior sales (orders 6-15)
  -- This measures whether demand is accelerating or decelerating (by units sold)
  sales_velocity AS (
    SELECT
      product_id,
      -- Units sold in the most recent 5 orders per product
      SUM(quantity) FILTER (WHERE rn <= 5) AS recent_sales,
      -- Units sold in orders 6-15 per product (prior period)
      SUM(quantity) FILTER (WHERE rn > 5 AND rn <= 15) AS prior_sales,
      -- Total units sold for reference
      SUM(quantity) AS total_sales
    FROM (
      SELECT
        product_id,
        quantity,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY effective_updated_at DESC) AS rn
      FROM delivered_order_lines
    ) ranked_sales
    WHERE rn <= 15
    GROUP BY product_id
  ),

  -- Rank products by popularity (units sold) within category
  popularity_score AS (
    SELECT
      product_id,
      category,
      SUM(quantity) AS sale_count,
      RANK() OVER (PARTITION BY category ORDER BY SUM(quantity) DESC) AS popularity_rank
    FROM delivered_order_lines
    GROUP BY product_id, category
  ),

  -- Calculate total stock across all stores per product and rank by scarcity
  inventory_status AS (
    SELECT
      product_id,
      SUM(stock_level) AS total_stock,
      RANK() OVER (ORDER BY SUM(stock_level) ASC) AS scarcity_rank
    FROM store_inventory
    GROUP BY product_id
  ),

  -- Identify high demand products (above average sales)
  high_demand_products AS (
    SELECT
      product_id,
      sale_count,
      CASE
        WHEN sale_count > (SELECT AVG(sale_count) FROM popularity_score) THEN TRUE
        ELSE FALSE
      END AS is_high_demand
    FROM popularity_score
  ),

  -- Combine all product-level pricing factors
  pricing_factors AS (
    SELECT
      ps.product_id,
      ps.category,
      ps.sale_count,
      ps.popularity_rank,

      -- Popularity adjustment: Top 3 get 20% premium, 4-10 get 10%, rest get 10% discount
      CASE
        WHEN ps.popularity_rank <= 3 THEN 1.20
        WHEN ps.popularity_rank BETWEEN 4 AND 10 THEN 1.10
        ELSE 0.90
      END AS popularity_adjustment,

      -- Stock scarcity adjustment: Low stock (high scarcity rank) gets premium
      CASE
        WHEN inv.scarcity_rank <= 3 THEN 1.15
        WHEN inv.scarcity_rank BETWEEN 4 AND 10 THEN 1.08
        WHEN inv.scarcity_rank BETWEEN 11 AND 20 THEN 1.00
        ELSE 0.95
      END AS scarcity_adjustment,

      -- Demand multiplier: Based on sales velocity (recent vs prior sales)
      CASE
        WHEN sv.prior_sales > 0 THEN
          LEAST(GREATEST(
            1.0 + ((sv.recent_sales::numeric / sv.prior_sales) - 1.0) * 0.25,
            0.85
          ), 1.25)
        WHEN sv.recent_sales > 0 THEN 1.10  -- New demand with no prior history
        ELSE 1.0
      END AS demand_multiplier,

      -- High demand flag for additional premium
      CASE WHEN hd.is_high_demand THEN 1.05 ELSE 1.0 END AS demand_premium,

      -- MARKET BASKET ADJUSTMENT: Discount basket drivers to pull through sales
      -- Basket drivers get slight discount to encourage purchase of complementary items
      CASE
        WHEN bm.is_basket_driver THEN 0.95  -- 5% discount for basket drivers
        WHEN bm.num_affinity_products >= 3 THEN 0.98  -- Small discount for products with affinities
        ELSE 1.0
      END AS basket_adjustment,

      inv.total_stock,
      sv.recent_sales,
      sv.prior_sales,
      sv.total_sales,
      bm.num_affinity_products,
      bm.is_basket_driver

    FROM popularity_score ps
    LEFT JOIN inventory_status inv ON inv.product_id = ps.product_id
    LEFT JOIN sales_velocity sv ON sv.product_id = ps.product_id
    LEFT JOIN high_demand_products hd ON hd.product_id = ps.product_id
    LEFT JOIN basket_metrics bm ON bm.product_id = ps.product_id
  )

-- Final SELECT: Apply all adjustments to each inventory item
SELECT
  inv.inventory_id,
  inv.store_id,
  inv.store_name,
  inv.store_zone,
  inv.product_id,
  inv.product_name,
  inv.category,
  inv.stock_level,
  inv.reserved_quantity,
  inv.available_quantity,
  inv.perishable,
  inv.unit_price AS base_price,

  -- Store-specific adjustments
  CASE
    WHEN inv.store_zone = 'MAN' THEN 1.15
    WHEN inv.store_zone = 'BK' THEN 1.05
    WHEN inv.store_zone = 'QNS' THEN 1.00
    WHEN inv.store_zone = 'BX' THEN 0.98
    WHEN inv.store_zone = 'SI' THEN 0.95
    ELSE 1.00
  END AS zone_adjustment,

  -- Perishable discount to move inventory faster
  CASE
    WHEN inv.perishable = TRUE THEN 0.95
    ELSE 1.0
  END AS perishable_adjustment,

  -- Low available stock at this specific store gets additional premium
  CASE
    WHEN inv.available_quantity <= 5 THEN 1.10
    WHEN inv.available_quantity <= 15 THEN 1.03
    ELSE 1.0
  END AS local_stock_adjustment,

  -- Product-level factors from CTEs
  pf.popularity_adjustment,
  pf.scarcity_adjustment,
  pf.demand_multiplier,
  pf.demand_premium,
  pf.basket_adjustment,
  pf.sale_count AS product_sale_count,
  pf.total_stock AS product_total_stock,

  -- Computed dynamic price with 8 factors (matches Materialize exactly)
  ROUND(
    (COALESCE(inv.unit_price, 0) *
    CASE WHEN inv.store_zone = 'MAN' THEN 1.15
         WHEN inv.store_zone = 'BK' THEN 1.05
         WHEN inv.store_zone = 'QNS' THEN 1.00
         WHEN inv.store_zone = 'BX' THEN 0.98
         WHEN inv.store_zone = 'SI' THEN 0.95
         ELSE 1.00 END *
    CASE WHEN inv.perishable = TRUE THEN 0.95 ELSE 1.0 END *
    CASE WHEN inv.available_quantity <= 5 THEN 1.10
         WHEN inv.available_quantity <= 15 THEN 1.03
         ELSE 1.0 END *
    COALESCE(pf.popularity_adjustment, 1.0) *
    COALESCE(pf.scarcity_adjustment, 1.0) *
    COALESCE(pf.demand_multiplier, 1.0) *
    COALESCE(pf.demand_premium, 1.0) *
    COALESCE(pf.basket_adjustment, 1.0))::numeric,
    2
  ) AS live_price,

  -- Price difference for easy comparison
  ROUND(
    ((COALESCE(inv.unit_price, 0) *
      CASE WHEN inv.store_zone = 'MAN' THEN 1.15
           WHEN inv.store_zone = 'BK' THEN 1.05
           WHEN inv.store_zone = 'QNS' THEN 1.00
           WHEN inv.store_zone = 'BX' THEN 0.98
           WHEN inv.store_zone = 'SI' THEN 0.95
           ELSE 1.00 END *
      CASE WHEN inv.perishable = TRUE THEN 0.95 ELSE 1.0 END *
      CASE WHEN inv.available_quantity <= 5 THEN 1.10
           WHEN inv.available_quantity <= 15 THEN 1.03
           ELSE 1.0 END *
      COALESCE(pf.popularity_adjustment, 1.0) *
      COALESCE(pf.scarcity_adjustment, 1.0) *
      COALESCE(pf.demand_multiplier, 1.0) *
      COALESCE(pf.demand_premium, 1.0) *
      COALESCE(pf.basket_adjustment, 1.0)
    ) - COALESCE(inv.unit_price, 0))::numeric,
    2
  ) AS price_change,

  inv.effective_updated_at

FROM store_inventory inv
LEFT JOIN pricing_factors pf ON pf.product_id = inv.product_id
WHERE inv.unit_price IS NOT NULL;

-- =============================================================================
-- Step 3: Create MATERIALIZED VIEW version (pre-computed, FAST but STALE)
-- Refreshed every 20 seconds to simulate batch processing
-- Same complex logic as the VIEW but pre-computed
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS inventory_items_with_dynamic_pricing_batch AS
SELECT * FROM inventory_items_with_dynamic_pricing;

-- Index for efficient inventory item lookup on the batch materialized view
CREATE INDEX IF NOT EXISTS inventory_dynamic_pricing_batch_inv_idx
ON inventory_items_with_dynamic_pricing_batch (inventory_id);

CREATE INDEX IF NOT EXISTS inventory_dynamic_pricing_batch_product_idx
ON inventory_items_with_dynamic_pricing_batch (product_id);

-- Update refresh log to track this materialized view
INSERT INTO materialized_view_refresh_log (view_name, last_refresh)
VALUES ('inventory_items_with_dynamic_pricing_batch', NOW())
ON CONFLICT (view_name) DO NOTHING;

-- Insert migration record
INSERT INTO schema_migrations (version) VALUES ('081_dynamic_pricing_views')
ON CONFLICT (version) DO NOTHING;
