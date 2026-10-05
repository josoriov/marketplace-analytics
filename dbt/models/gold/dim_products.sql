with cleaned as (
    select
        nullif(btrim(product_id), '')::varchar(32) as product_id,
        nullif(btrim(product_category_name), '')::varchar as source_product_category_name,
        product_name_lenght as product_name_length,
        product_description_lenght as product_description_length,
        product_photos_qty,
        product_weight_g,
        product_length_cm,
        product_height_cm,
        product_width_cm
    from {{ source('raw', 'products') }}
), translated as (
    select p.*, ct.product_category_name_english
    from cleaned as p
    left join {{ ref('category_translation') }} as ct
        on p.source_product_category_name = ct.product_category_name
)
select distinct on (product_id)
    product_id,
    coalesce(product_category_name_english, source_product_category_name) as product_category_name,
    product_category_name_english,
    source_product_category_name,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
from translated
where product_id is not null
order by product_id, product_category_name_english nulls last,
    source_product_category_name nulls last, product_name_length nulls last,
    product_description_length nulls last, product_photos_qty nulls last,
    product_weight_g nulls last, product_length_cm nulls last,
    product_height_cm nulls last, product_width_cm nulls last
