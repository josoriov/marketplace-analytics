-- Performance indexes for the raw and analytics layers.
--
-- Each index targets a column that appears frequently in JOINs, WHERE
-- filters, or GROUP BY clauses used by the fact tables and marts.
-- Using IF NOT EXISTS keeps the script safe for repeated pipeline runs.

-- ── Raw schema ──────────────────────────────────────────────────────

-- orders: join target for fact_orders and review lookups
CREATE INDEX IF NOT EXISTS idx_orders_order_id
    ON raw.orders (order_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON raw.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts
    ON raw.orders (order_purchase_timestamp);

-- order_items: join target for every mart aggregation
CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON raw.order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON raw.order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
    ON raw.order_items (seller_id);

-- order_payments: aggregated by order_id in fact_order_items
CREATE INDEX IF NOT EXISTS idx_order_payments_order_id
    ON raw.order_payments (order_id);

-- order_reviews: joined to orders in every mart
CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id
    ON raw.order_reviews (order_id);

-- customers: filtered and grouped by geography in mart_geography_sales
CREATE INDEX IF NOT EXISTS idx_customers_customer_id
    ON raw.customers (customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_state
    ON raw.customers (customer_state);

-- products: joined in mart_category_performance
CREATE INDEX IF NOT EXISTS idx_products_product_id
    ON raw.products (product_id);

-- sellers: joined in mart_seller_performance
CREATE INDEX IF NOT EXISTS idx_sellers_seller_id
    ON raw.sellers (seller_id);
CREATE INDEX IF NOT EXISTS idx_sellers_state
    ON raw.sellers (seller_state);
