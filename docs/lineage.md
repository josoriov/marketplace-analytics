# Model lineage

The dbt project builds three layers of views. Raw CSVs are loaded by the Python
pipeline into the nine `raw` tables; dbt then builds six `silver` views and eight
`analytics` views on top of them. Sources, models, and tests are declared in
`dbt/models`.

## Layers

| Layer | Objects |
| --- | --- |
| `raw` | 9 source tables: orders, order_items, order_payments, order_reviews, customers, products, sellers, category_translation, geolocation |
| `silver` | 6 views: orders, order_items, order_item_summary, order_payment_summary, order_review_summary, category_translation |
| `analytics` | 3 dimensions (customers, products, sellers), 2 facts (orders, order_items), 3 marts (seller, category, geography) |

## Lineage

```mermaid
flowchart LR
    ro[raw.orders] --> so[silver.orders] --> fo[analytics.fact_orders]
    rr[raw.order_reviews] --> sr[silver.order_review_summary] --> fo
    ri[raw.order_items] --> si[silver.order_items]
    si --> totals[silver.order_item_summary]
    si --> fi[analytics.fact_order_items]
    rp[raw.order_payments] --> sp[silver.order_payment_summary] --> fi
    rc[raw.customers] --> dc[analytics.dim_customers]
    rs[raw.sellers] --> ds[analytics.dim_sellers]
    rpr[raw.products] --> dp[analytics.dim_products]
    rt[raw.category_translation] --> st[silver.category_translation] --> dp
    fi --> ms[analytics.mart_seller_performance]
    fo --> ms
    ds --> ms
    fi --> mc[analytics.mart_category_performance]
    fo --> mc
    dp --> mc
    fo --> mg[analytics.mart_geography_sales]
    totals --> mg
    dc --> mg
    rg[raw.geolocation: loaded, unused]
```

Reading the graph:

- `fact_orders` joins cleaned orders to per-order review summaries.
- `fact_order_items` joins cleaned items to per-order payment summaries.
- Seller/category marts read both facts and their dimensions; geography reads
  `fact_orders`, `dim_customers`, and `silver.order_item_summary` for full
  per-order price plus freight.
- `raw.geolocation` is loaded and validated but not referenced by any model.

## Interactive lineage

Generate and serve the dbt documentation to explore the model DAG and descriptions
in a browser. The default dbt v2 generation does not include column-level lineage:

```bash
uv run --locked python -m app.etl.transform docs generate
uv run --locked python -m app.etl.transform docs serve --port 8080
```

The generated `dbt/target/` artifacts are gitignored; regenerate them locally.
