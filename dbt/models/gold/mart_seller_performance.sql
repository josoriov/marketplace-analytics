-- multi-seller orders contribute only this seller's prices and freight.
with seller_orders as (
    select
        seller_id,
        order_id,
        count(*) as total_items,
        sum(price) as revenue,
        sum(freight_value) as freight
    from {{ ref('fact_order_items') }}
    group by seller_id, order_id
)
select
    s.seller_id,
    s.seller_city,
    s.seller_state,
    count(*) as total_orders,
    sum(so.total_items)::bigint as total_items_sold,
    coalesce(sum(so.revenue), 0) as total_revenue,
    round(avg(so.revenue), 2) as avg_order_value,
    round(avg(so.freight), 2) as avg_freight_value,
    round(avg(fo.avg_review_score), 2) as avg_review_score,
    round(avg(fo.delivery_delay_days)
        filter (where fo.has_delivery_outcome), 2) as avg_delivery_delay_days,
    round(
        avg(case when fo.is_late_delivery then 1.0 else 0.0 end)
            filter (where fo.has_delivery_outcome),
        4
    ) as late_delivery_rate
from {{ ref('dim_sellers') }} as s
inner join seller_orders as so on s.seller_id = so.seller_id
inner join {{ ref('fact_orders') }} as fo on so.order_id = fo.order_id
where fo.is_delivered
group by s.seller_id, s.seller_city, s.seller_state
