-- reviews/delivery are order-weighted; price is item-weighted.
with category_orders as (
    select
        coalesce(p.product_category_name, 'unknown') as product_category,
        fi.order_id,
        count(*) as total_items,
        count(fi.price) as priced_items,
        sum(fi.price) as revenue
    from {{ ref('fact_order_items') }} as fi
    left join {{ ref('dim_products') }} as p on fi.product_id = p.product_id
    group by coalesce(p.product_category_name, 'unknown'), fi.order_id
)
select
    co.product_category,
    count(*) as total_orders,
    sum(co.total_items)::bigint as total_items_sold,
    coalesce(sum(co.revenue), 0) as total_revenue,
    round(sum(co.revenue) / nullif(sum(co.priced_items), 0), 2) as avg_price,
    round(avg(fo.avg_review_score), 2) as avg_review_score,
    round(
        avg(case when fo.is_late_delivery then 1.0 else 0.0 end)
            filter (where fo.has_delivery_outcome),
        4
    ) as late_delivery_rate
from category_orders as co
inner join {{ ref('fact_orders') }} as fo on co.order_id = fo.order_id
where fo.is_delivered
group by co.product_category
