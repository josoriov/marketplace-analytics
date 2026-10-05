select
    nullif(btrim(order_id), '')::varchar(32) as order_id,
    order_item_id,
    nullif(btrim(product_id), '')::varchar(32) as product_id,
    nullif(btrim(seller_id), '')::varchar(32) as seller_id,
    price,
    freight_value
from {{ source('raw', 'order_items') }}
where nullif(btrim(order_id), '') is not null
