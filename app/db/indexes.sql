create index if not exists idx_orders_order_id
    on raw.orders (order_id);
create index if not exists idx_orders_customer_id
    on raw.orders (customer_id);
create index if not exists idx_orders_purchase_ts
    on raw.orders (order_purchase_timestamp);
create index if not exists idx_order_items_order_id
    on raw.order_items (order_id);
create index if not exists idx_order_items_product_id
    on raw.order_items (product_id);
create index if not exists idx_order_items_seller_id
    on raw.order_items (seller_id);
create index if not exists idx_order_payments_order_id
    on raw.order_payments (order_id);
create index if not exists idx_order_reviews_order_id
    on raw.order_reviews (order_id);
create index if not exists idx_customers_customer_id
    on raw.customers (customer_id);
create index if not exists idx_customers_state
    on raw.customers (customer_state);
create index if not exists idx_products_product_id
    on raw.products (product_id);
create index if not exists idx_sellers_seller_id
    on raw.sellers (seller_id);
create index if not exists idx_sellers_state
    on raw.sellers (seller_state);
