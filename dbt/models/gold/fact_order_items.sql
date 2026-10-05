select
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value as item_total_value,
    ops.total_payment_value as order_total_payment_value
from {{ ref('order_items') }} as oi
left join {{ ref('order_payment_summary') }} as ops on oi.order_id = ops.order_id
