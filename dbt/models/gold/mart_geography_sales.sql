-- tickets include all item prices plus freight for each delivered order.
select
    c.customer_state,
    c.customer_city,
    count(*) as total_orders,
    coalesce(sum(ot.revenue), 0) as total_revenue,
    round(avg(ot.revenue + ot.freight), 2) as avg_ticket,
    round(avg(fo.avg_review_score), 2) as avg_review_score
from {{ ref('dim_customers') }} as c
inner join {{ ref('fact_orders') }} as fo on c.customer_id = fo.customer_id
inner join {{ ref('order_item_summary') }} as ot on fo.order_id = ot.order_id
where fo.is_delivered
group by c.customer_state, c.customer_city
