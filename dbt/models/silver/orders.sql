select
    nullif(btrim(order_id), '')::varchar(32) as order_id,
    nullif(btrim(customer_id), '')::varchar(32) as customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date
from {{ source('raw', 'orders') }}
where nullif(btrim(order_id), '') is not null
