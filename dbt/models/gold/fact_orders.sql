select
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    extract(epoch from (
        o.order_delivered_customer_date - o.order_estimated_delivery_date
    )) / 86400.0 as delivery_delay_days,
    (o.order_status = 'delivered') as is_delivered,
    (
        o.order_delivered_customer_date is not null
        and o.order_estimated_delivery_date is not null
        and o.order_delivered_customer_date > o.order_estimated_delivery_date
    ) as is_late_delivery,
    (
        o.order_status = 'delivered'
        and o.order_delivered_customer_date is not null
        and o.order_estimated_delivery_date is not null
    ) as has_delivery_outcome,
    reviews.avg_review_score
from {{ ref('orders') }} as o
left join {{ ref('order_review_summary') }} as reviews on o.order_id = reviews.order_id
