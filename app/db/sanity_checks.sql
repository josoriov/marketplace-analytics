-- Post-transformation sanity checks.
--
-- Each check runs a query that should return zero rows when the analytics
-- layer is healthy.  The pipeline runner executes this script and treats any
-- returned rows as a signal that something is wrong.
--
-- The script uses a single DO block so every check is evaluated inside one
-- transaction.  Failures are raised as exceptions that the pipeline can catch.

DO $$
DECLARE
    _count BIGINT;
BEGIN
    -- 1. fact_orders must contain rows.
    SELECT COUNT(*) INTO _count FROM analytics.fact_orders;
    IF _count = 0 THEN
        RAISE EXCEPTION 'sanity: fact_orders is empty';
    END IF;

    -- 2. fact_order_items must contain rows.
    SELECT COUNT(*) INTO _count FROM analytics.fact_order_items;
    IF _count = 0 THEN
        RAISE EXCEPTION 'sanity: fact_order_items is empty';
    END IF;

    -- 3. No duplicate order_id in fact_orders (grain = one row per order).
    SELECT COUNT(*) INTO _count
    FROM (
        SELECT order_id
        FROM analytics.fact_orders
        GROUP BY order_id
        HAVING COUNT(*) > 1
    ) AS dupes;
    IF _count > 0 THEN
        RAISE EXCEPTION 'sanity: % duplicate order_id(s) in fact_orders', _count;
    END IF;

    -- 4. Late delivery rate must be between 0 and 1 for every seller.
    SELECT COUNT(*) INTO _count
    FROM analytics.mart_seller_performance
    WHERE late_delivery_rate < 0 OR late_delivery_rate > 1;
    IF _count > 0 THEN
        RAISE EXCEPTION 'sanity: % seller(s) with late_delivery_rate outside [0,1]', _count;
    END IF;

    -- 5. Average review score must be in the valid 1–5 range.
    SELECT COUNT(*) INTO _count
    FROM analytics.mart_seller_performance
    WHERE avg_review_score < 1 OR avg_review_score > 5;
    IF _count > 0 THEN
        RAISE EXCEPTION 'sanity: % seller(s) with avg_review_score outside [1,5]', _count;
    END IF;

    -- 6. Revenue must be non-negative everywhere.
    SELECT COUNT(*) INTO _count
    FROM analytics.mart_seller_performance
    WHERE total_revenue < 0;
    IF _count > 0 THEN
        RAISE EXCEPTION 'sanity: % seller(s) with negative total_revenue', _count;
    END IF;

    SELECT COUNT(*) INTO _count
    FROM analytics.mart_category_performance
    WHERE total_revenue < 0;
    IF _count > 0 THEN
        RAISE EXCEPTION 'sanity: % category(ies) with negative total_revenue', _count;
    END IF;

    SELECT COUNT(*) INTO _count
    FROM analytics.mart_geography_sales
    WHERE total_revenue < 0;
    IF _count > 0 THEN
        RAISE EXCEPTION 'sanity: % geography row(s) with negative total_revenue', _count;
    END IF;

    RAISE NOTICE 'All sanity checks passed';
END
$$;
