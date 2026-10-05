with cleaned as (
    select
        nullif(btrim(seller_id), '')::varchar(32) as seller_id,
        nullif(btrim(seller_city), '')::varchar as seller_city,
        nullif(btrim(seller_state), '')::varchar(2) as seller_state
    from {{ source('raw', 'sellers') }}
)
select distinct on (seller_id) *
from cleaned
where seller_id is not null
order by seller_id, seller_city nulls last, seller_state nulls last
