-- multiple payment components are valid and must all contribute to the total.
select
    nullif(btrim(order_id), '')::varchar(32) as order_id,
    sum(payment_value) as total_payment_value
from {{ source('raw', 'order_payments') }}
where nullif(btrim(order_id), '') is not null
group by nullif(btrim(order_id), '')::varchar(32)
