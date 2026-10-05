select
    order_id,
    sum(price) as revenue,
    sum(freight_value) as freight
from {{ ref('order_items') }}
group by order_id
