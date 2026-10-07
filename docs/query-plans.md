# Query plans and index effect

Measured 2026-10-07 against the full Olist dataset in an isolated Compose
PostgreSQL 16 database (9 raw tables, 1,550,922 source rows). Queries were read
directly from the four business handlers in `app/main.py`, including bind
parameters. [Captured plans and timings](query-plans.txt) are committed.

## Method

Each query had one warm-up and three timed runs per mode, on the same database:

- **Planner defaults**: indexes from `app/db/indexes.sql` are present.
- **Index scans disabled**: `set enable_indexscan = off; set enable_indexonlyscan = off; set enable_bitmapscan = off;`

The table reports median execution time. A further run captured each text plan.
Disabling scan methods discourages their use; it does not emulate dropping the
indexes or measure their write/storage cost. Runs were sequential and cache-warm;
these small samples do not establish a statistically significant speedup.

```sql
explain (analyze, buffers)
select * from analytics.mart_seller_performance
order by total_revenue desc, seller_id limit 10;

explain (analyze, buffers)
select * from analytics.mart_seller_performance
where seller_id = '4869f7a5dfa277a7dca6462dcf3b52b2';

explain (analyze, buffers)
select * from analytics.mart_category_performance
order by total_revenue desc, product_category limit 100;

explain (analyze, buffers)
select c.customer_state, count(*) as total_orders,
       coalesce(sum(ot.revenue), 0) as total_revenue,
       round(avg(ot.revenue + ot.freight), 2) as avg_ticket,
       round(avg(fo.avg_review_score), 2) as avg_review_score
from analytics.dim_customers as c
inner join analytics.fact_orders as fo on c.customer_id = fo.customer_id
inner join silver.order_item_summary as ot on fo.order_id = ot.order_id
where fo.is_delivered
group by c.customer_state
order by total_revenue desc, c.customer_state nulls last limit 100;
```

## Results

| Endpoint | Planner defaults | Index scans disabled |
| --- | --- | --- |
| `/sellers/top?limit=10` | 1255 ms | 1264 ms |
| `/sellers/{id}/performance` | 621 ms | 623 ms |
| `/categories/performance?limit=100` | 1461 ms | 1454 ms |
| `/geography/states?limit=100` | 1096 ms | 1088 ms |

Business plans use sequential scans, joins, aggregates, and sorts, with no index
or bitmap scans in the captured plans. No business API index speedup is supported
by these measurements. JIT compilation alone took about 395–790 ms in the
representative plans, so elapsed time is not simply aggregation or disk I/O.

The seller-detail filter **does push down** to `raw.order_items`: its parallel
scan filters the normalized `seller_id` before grouping. However, the predicate
uses `nullif(btrim(seller_id), '')::varchar(32)`, which does not match the ordinary
index on raw `seller_id`; reviews and orders still require broad processing.
`GROUP BY` is not a general barrier to predicate pushdown; PostgreSQL can push
safe predicates into aggregate subqueries. See its
[optimizer implementation](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/optimizer/path/allpaths.c).

## Point lookup

An untransformed keyed lookup uses the existing index:

```sql
explain (analyze, buffers)
select * from raw.order_items
where order_id = '00010242fe8c5a6d1ba2dd792cb16214';
```

The JSON plan measurement was **0.025 ms** with `idx_order_items_order_id`, versus
**5.079 ms** with sequential scans. The additional text-plan runs and exact
parameters are in the captured artifact. These are illustrative single lookups.
The reload uses `TRUNCATE` and inserts; indexes do not accelerate that write path.

Keep ordinary views for this dataset. If API latency becomes a requirement,
measure normalization expressions, JIT overhead, and materialization before
choosing an optimization; no indexes or models were changed for this review.
