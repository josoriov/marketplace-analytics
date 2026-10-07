# Example queries and findings

All numbers below come from the full Olist dataset loaded by the pipeline into the
Compose PostgreSQL 16 (dates captured 2026-10-07). Revenue means the sum of item
prices excluding freight unless stated otherwise; the definitions live in
[README.md](../README.md#metrics).
Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
by Olist, under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The tables, findings, and sample responses below are derived aggregations of that
dataset and are shared under the same license; the application code is MIT.

## Five example queries

**E1 — Top sellers by delivered revenue** (`analytics.mart_seller_performance`):

```sql
select seller_id, seller_state, total_orders, total_revenue, avg_review_score
from analytics.mart_seller_performance
order by total_revenue desc, seller_id limit 5;
```

| seller_id | state | orders | revenue | avg review |
| --- | --- | --- | --- | --- |
| 4869f7a5dfa277a7dca6462dcf3b52b2 | SP | 1124 | 226,987.93 | 4.15 |
| 53243585a1d6dc2643021fd1853d8905 | BA | 348 | 217,940.44 | 4.19 |
| 4a3ca9315b744ce9f8e9374361493884 | SP | 1772 | 196,882.12 | 3.85 |
| fa1c13f2614d7b5c4749cbc52fecda94 | SP | 578 | 190,917.14 | 4.37 |
| 7c67e1448b00f6e969d365cea6b010ab | SP | 973 | 186,570.05 | 3.50 |

**E2 — Category mix** (`analytics.mart_category_performance`):

```sql
select product_category, total_orders, total_items_sold, total_revenue, late_delivery_rate
from analytics.mart_category_performance
order by total_revenue desc, product_category limit 5;
```

| category | orders | items | revenue | late rate |
| --- | --- | --- | --- | --- |
| health_beauty | 8,647 | 9,465 | 1,233,131.72 | 0.0896 |
| watches_gifts | 5,495 | 5,859 | 1,166,176.98 | 0.0852 |
| bed_bath_table | 9,272 | 10,953 | 1,023,434.76 | 0.0875 |
| sports_leisure | 7,530 | 8,431 | 954,852.55 | 0.0776 |
| computers_accessories | 6,530 | 7,644 | 888,724.61 | 0.0770 |

**E3 — Revenue by customer state** (facts + customer dimension):

```sql
select c.customer_state,
       count(*) as delivered_orders,
       round(sum(ot.revenue), 2) as item_revenue
from analytics.fact_orders fo
join analytics.dim_customers c using (customer_id)
join silver.order_item_summary ot using (order_id)
where fo.is_delivered
group by c.customer_state
order by item_revenue desc, c.customer_state nulls last limit 5;
```

| state | delivered orders | item revenue |
| --- | --- | --- |
| SP | 40,501 | 5,067,633.16 |
| RJ | 12,350 | 1,759,651.13 |
| MG | 11,354 | 1,552,481.83 |
| RS | 5,345 | 728,897.47 |
| PR | 4,923 | 666,063.51 |

**E4 — Review score by delivery timeliness** (`analytics.fact_orders`):

```sql
select is_late_delivery,
       count(*) as orders,
       round(avg(avg_review_score), 2) as avg_review_score
from analytics.fact_orders
where has_delivery_outcome and avg_review_score is not null
group by is_late_delivery order by is_late_delivery;
```

| late? | orders | avg review |
| --- | --- | --- |
| no | 88,163 | 4.29 |
| yes | 7,661 | 2.57 |

**E5 — Freight share of delivered item value** (`analytics.fact_order_items`):

```sql
select round(sum(price), 2) as item_revenue,
       round(sum(freight_value), 2) as freight,
       round(100 * sum(freight_value) / sum(price), 2) as freight_pct_of_items
from analytics.fact_order_items i
join analytics.fact_orders o using (order_id)
where o.is_delivered;
```

| item revenue | freight | freight % of items |
| --- | --- | --- |
| 13,221,498.11 | 2,198,275.64 | 16.63% |

## Verified findings

### F1 — Late deliveries score lower, and 8.11% of eligible orders are late

- **Assumptions**: an order is *eligible* when it is delivered and has both actual
  and estimated delivery timestamps (`has_delivery_outcome`); it is *late* when
  the actual delivery timestamp exceeds the estimate; an order's review score is the mean
  of its non-null review scores. Only orders with a review enter the averages.
- **Result**: 7,826 of 96,470 eligible orders were late (**8.11%**). Among the
  95,824 eligible orders with reviews, 7,661 were late; these late orders average
  **2.57** vs **4.29** for on-time reviewed orders (query E4).
- **Caveat**: this is an association, not a proven cause; route length, seller, and
  category are not controlled for.

The overall rate includes eligible orders without reviews:

```sql
select count(*) as eligible_orders,
       count(*) filter (where is_late_delivery) as late_orders,
       round(100.0 * count(*) filter (where is_late_delivery) / count(*), 2) as late_pct
from analytics.fact_orders
where has_delivery_outcome;
```

### F2 — The top 10 sellers account for 13.27% of delivered revenue

- **Assumptions**: revenue is delivered item price excluding freight; a
  multi-seller order attributes each item's revenue to its own seller, so seller
  revenues are additive while seller order counts overlap. Unmatched sellers are
  excluded; source-revenue reconciliation verifies this matching policy.
- **Result**: the top 10 of 2,970 sellers account for **13.27%** of the
  13,221,498.11 delivered item revenue (**1,754,800.00** for the top 10).
  This share alone does not measure concentration among all remaining sellers.

```sql
with s as (
  select total_revenue, row_number() over (order by total_revenue desc) as rn
  from analytics.mart_seller_performance
)
select round(sum(total_revenue) filter (where rn <= 10), 2) as top10_revenue,
       round(100 * sum(total_revenue) filter (where rn <= 10) / sum(total_revenue), 2) as top10_pct
from s;
```

### F3 — MA's late-delivery rate is about 2.4× the national rate

- **Assumptions**: same eligibility rule as F1; state comes from the customer
  delivery address; states restricted to those with at least 500 eligible orders.
- **Result**: the highest rates are MA **19.7%**, CE **15.3%**, BA **14.0%**, and
  RJ **13.5%**, against a national **8.11%** — MA is roughly 2.4× the baseline.

```sql
select c.customer_state,
       count(*) filter (where fo.has_delivery_outcome) as eligible,
       round(count(*) filter (where fo.is_late_delivery)::numeric
             / nullif(count(*) filter (where fo.has_delivery_outcome), 0), 4) as late_rate
from analytics.fact_orders fo
join analytics.dim_customers c using (customer_id)
where fo.is_delivered
group by c.customer_state
having count(*) filter (where fo.has_delivery_outcome) >= 500
order by late_rate desc, c.customer_state nulls last limit 5;
```

## Sample API output

The four business routes in `app/main.py` expose metrics; F1–F3 use the same
underlying facts (late-delivery rate by state is not a route). Representative
responses (`curl 'http://localhost:8000/...'`):

`/sellers/top?limit=1`:

```json
[{"seller_id":"4869f7a5dfa277a7dca6462dcf3b52b2","seller_city":"guariba",
  "seller_state":"SP","total_orders":1124,"total_items_sold":1148,
  "total_revenue":"226987.93","avg_order_value":"201.95","avg_freight_value":"17.81",
  "avg_review_score":"4.15","avg_delivery_delay_days":"-10.39","late_delivery_rate":"0.1157"}]
```

`/geography/states?limit=3`:

```json
[{"customer_state":"SP","total_orders":40501,"total_revenue":"5067633.16",
  "avg_ticket":"142.46","avg_review_score":"4.25"},
 {"customer_state":"RJ","total_orders":12350,"total_revenue":"1759651.13",
  "avg_ticket":"166.43","avg_review_score":"3.97"},
 {"customer_state":"MG","total_orders":11354,"total_revenue":"1552481.83",
  "avg_ticket":"160.20","avg_review_score":"4.19"}]
```

Decimal metrics are JSON strings (e.g. `"226987.93"`), counts are integers, and
missing values are JSON `null`, as documented in README.
