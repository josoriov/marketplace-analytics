-- review_id can repeat across orders; keep every score before averaging by order.
select
    nullif(btrim(order_id), '')::varchar(32) as order_id,
    avg(review_score) as avg_review_score
from {{ source('raw', 'order_reviews') }}
where nullif(btrim(order_id), '') is not null
group by nullif(btrim(order_id), '')::varchar(32)
