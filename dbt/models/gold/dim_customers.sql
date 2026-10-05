with cleaned as (
    select
        nullif(btrim(customer_id), '')::varchar(32) as customer_id,
        nullif(btrim(customer_unique_id), '')::varchar(32) as customer_unique_id,
        nullif(btrim(customer_city), '')::varchar as customer_city,
        nullif(btrim(customer_state), '')::varchar(2) as customer_state
    from {{ source('raw', 'customers') }}
)
select distinct on (customer_id) *
from cleaned
where customer_id is not null
order by customer_id, customer_unique_id nulls last,
    customer_city nulls last, customer_state nulls last
