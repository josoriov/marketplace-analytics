with cleaned as (
    select
        nullif(btrim(product_category_name), '')::varchar as product_category_name,
        nullif(btrim(product_category_name_english), '')::varchar as product_category_name_english
    from {{ source('raw', 'category_translation') }}
)
select distinct on (product_category_name) *
from cleaned
where product_category_name is not null
order by product_category_name, product_category_name_english nulls last
