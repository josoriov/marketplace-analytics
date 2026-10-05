CREATE SCHEMA IF NOT EXISTS analytics;

-- Keep customer dimensions at one row per customer_id for stable joins.
CREATE OR REPLACE VIEW analytics.dim_customers AS
WITH ranked_customers AS (
    SELECT
        customer_id,
        customer_unique_id,
        customer_city,
        customer_state,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY
                customer_unique_id NULLS LAST,
                customer_city NULLS LAST,
                customer_state NULLS LAST
        ) AS row_num
    FROM raw.customers
    WHERE customer_id IS NOT NULL
)
SELECT
    customer_id,
    customer_unique_id,
    customer_city,
    customer_state
FROM ranked_customers
WHERE row_num = 1;

-- Normalize product naming and expose translated category labels for analytics.
CREATE OR REPLACE VIEW analytics.dim_products AS
WITH translated_products AS (
    SELECT
        p.product_id,
        p.product_category_name AS source_product_category_name,
        ct.product_category_name_english,
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name
        ) AS product_category_name,
        p.product_name_lenght AS product_name_length,
        p.product_description_lenght AS product_description_length,
        p.product_photos_qty,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm
    FROM raw.products AS p
    LEFT JOIN raw.category_translation AS ct
        ON p.product_category_name = ct.product_category_name
    WHERE p.product_id IS NOT NULL
),
ranked_products AS (
    SELECT
        product_id,
        product_category_name,
        product_category_name_english,
        source_product_category_name,
        product_name_length,
        product_description_length,
        product_photos_qty,
        product_weight_g,
        product_length_cm,
        product_height_cm,
        product_width_cm,
        ROW_NUMBER() OVER (
            PARTITION BY product_id
            ORDER BY
                product_category_name_english NULLS LAST,
                source_product_category_name NULLS LAST,
                product_name_length NULLS LAST,
                product_description_length NULLS LAST,
                product_photos_qty NULLS LAST,
                product_weight_g NULLS LAST,
                product_length_cm NULLS LAST,
                product_height_cm NULLS LAST,
                product_width_cm NULLS LAST
        ) AS row_num
    FROM translated_products
)
SELECT
    product_id,
    product_category_name,
    product_category_name_english,
    source_product_category_name,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
FROM ranked_products
WHERE row_num = 1;

-- Keep seller dimensions at one row per seller_id for downstream facts and marts.
CREATE OR REPLACE VIEW analytics.dim_sellers AS
WITH ranked_sellers AS (
    SELECT
        seller_id,
        seller_city,
        seller_state,
        ROW_NUMBER() OVER (
            PARTITION BY seller_id
            ORDER BY
                seller_city NULLS LAST,
                seller_state NULLS LAST
        ) AS row_num
    FROM raw.sellers
    WHERE seller_id IS NOT NULL
)
SELECT
    seller_id,
    seller_city,
    seller_state
FROM ranked_sellers
WHERE row_num = 1;

-- ─────────────────────────────────────────────────────────────────────
-- Fact tables
-- ─────────────────────────────────────────────────────────────────────

-- One row per order with delivery timing metrics derived from raw timestamps.
CREATE OR REPLACE VIEW analytics.fact_orders AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    -- Days between estimated and actual delivery (positive = late).
    EXTRACT(EPOCH FROM (
        o.order_delivered_customer_date - o.order_estimated_delivery_date
    )) / 86400.0 AS delivery_delay_days,
    -- Boolean flags for easy filtering and aggregation.
    (o.order_status = 'delivered') AS is_delivered,
    (
        o.order_delivered_customer_date IS NOT NULL
        AND o.order_estimated_delivery_date IS NOT NULL
        AND o.order_delivered_customer_date > o.order_estimated_delivery_date
    ) AS is_late_delivery
FROM raw.orders AS o
WHERE o.order_id IS NOT NULL;

-- One row per order–item with line-level revenue and the parent order's payment
-- summary pre-joined so downstream queries do not need a second aggregation.
CREATE OR REPLACE VIEW analytics.fact_order_items AS
WITH order_payment_summary AS (
    SELECT
        order_id,
        SUM(payment_value) AS total_payment_value
    FROM raw.order_payments
    GROUP BY order_id
)
SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.price,
    oi.freight_value,
    -- Convenience aggregates at the item grain.
    oi.price + oi.freight_value AS item_total_value,
    ops.total_payment_value AS order_total_payment_value
FROM raw.order_items AS oi
LEFT JOIN order_payment_summary AS ops
    ON oi.order_id = ops.order_id
WHERE oi.order_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────
-- Business marts
-- ─────────────────────────────────────────────────────────────────────

-- Seller-level KPIs: revenue, volume, review quality, and delivery reliability.
CREATE OR REPLACE VIEW analytics.mart_seller_performance AS
SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT fi.order_id)          AS total_orders,
    COUNT(fi.order_item_id)              AS total_items_sold,
    COALESCE(SUM(fi.price), 0)           AS total_revenue,
    ROUND(AVG(fi.price), 2)              AS avg_order_value,
    ROUND(AVG(fi.freight_value), 2)      AS avg_freight_value,
    ROUND(AVG(r.review_score), 2)        AS avg_review_score,
    ROUND(AVG(fo.delivery_delay_days), 2) AS avg_delivery_delay_days,
    -- Late delivery rate = fraction of delivered orders that arrived after the
    -- estimated date.  Only orders with a known delivery outcome count.
    ROUND(
        AVG(CASE WHEN fo.is_late_delivery THEN 1.0 ELSE 0.0 END)::numeric,
        4
    ) AS late_delivery_rate
FROM analytics.dim_sellers   AS s
INNER JOIN analytics.fact_order_items AS fi ON s.seller_id = fi.seller_id
LEFT JOIN analytics.fact_orders       AS fo ON fi.order_id  = fo.order_id
LEFT JOIN raw.order_reviews           AS r  ON fo.order_id  = r.order_id
GROUP BY s.seller_id, s.seller_city, s.seller_state;

-- Category-level KPIs: sales volume, pricing, quality, and delivery reliability.
CREATE OR REPLACE VIEW analytics.mart_category_performance AS
SELECT
    p.product_category_name              AS product_category,
    COUNT(DISTINCT fi.order_id)          AS total_orders,
    COUNT(fi.order_item_id)              AS total_items_sold,
    COALESCE(SUM(fi.price), 0)           AS total_revenue,
    ROUND(AVG(fi.price), 2)              AS avg_price,
    ROUND(AVG(r.review_score), 2)        AS avg_review_score,
    ROUND(
        AVG(CASE WHEN fo.is_late_delivery THEN 1.0 ELSE 0.0 END)::numeric,
        4
    ) AS late_delivery_rate
FROM analytics.dim_products          AS p
INNER JOIN analytics.fact_order_items AS fi ON p.product_id = fi.product_id
LEFT JOIN analytics.fact_orders       AS fo ON fi.order_id  = fo.order_id
LEFT JOIN raw.order_reviews           AS r  ON fo.order_id  = r.order_id
WHERE p.product_category_name IS NOT NULL
GROUP BY p.product_category_name;

-- Geography-level KPIs: order volume, revenue, ticket size, and review quality.
CREATE OR REPLACE VIEW analytics.mart_geography_sales AS
SELECT
    c.customer_state,
    c.customer_city,
    COUNT(DISTINCT fo.order_id)          AS total_orders,
    COALESCE(SUM(fi.price), 0)           AS total_revenue,
    ROUND(AVG(fi.price + fi.freight_value), 2) AS avg_ticket,
    ROUND(AVG(r.review_score), 2)        AS avg_review_score
FROM analytics.dim_customers           AS c
INNER JOIN analytics.fact_orders       AS fo ON c.customer_id = fo.customer_id
INNER JOIN analytics.fact_order_items  AS fi ON fo.order_id   = fi.order_id
LEFT JOIN raw.order_reviews            AS r  ON fo.order_id   = r.order_id
GROUP BY c.customer_state, c.customer_city;
