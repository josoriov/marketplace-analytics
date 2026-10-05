-- compare to bronze independently of fact joins; only normalize join keys.
with delivered_items as (
    select
        nullif(btrim(oi.seller_id), '') as seller_id,
        nullif(btrim(o.customer_id), '') as customer_id,
        oi.price
    from {{ source('raw', 'order_items') }} as oi
    inner join {{ source('raw', 'orders') }} as o
        on nullif(btrim(oi.order_id), '') = nullif(btrim(o.order_id), '')
    where o.order_status = 'delivered'
), comparisons as (
    select
        'seller' as mart,
        (select coalesce(sum(total_revenue), 0)
         from {{ ref('mart_seller_performance') }}) as actual,
        coalesce(sum(price), 0) as expected
    from delivered_items as di
    where exists (select 1 from {{ ref('dim_sellers') }} as s where s.seller_id = di.seller_id)
    union all
    select
        'category',
        (select coalesce(sum(total_revenue), 0)
         from {{ ref('mart_category_performance') }}),
        coalesce(sum(price), 0)
    from delivered_items
    union all
    select
        'geography',
        (select coalesce(sum(total_revenue), 0)
         from {{ ref('mart_geography_sales') }}),
        coalesce(sum(price), 0)
    from delivered_items as di
    where exists (select 1 from {{ ref('dim_customers') }} as c where c.customer_id = di.customer_id)
)
select * from comparisons where actual is distinct from expected
