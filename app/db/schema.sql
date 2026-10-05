create schema if not exists raw;

do $$
begin
    if not exists (
        select 1
        from pg_type t
        join pg_namespace n on n.oid = t.typnamespace
        where n.nspname = 'raw'
          and t.typname = 'order_status_enum'
    ) then
        create type raw.order_status_enum as enum (
            'unavailable',
            'shipped',
            'approved',
            'processing',
            'delivered',
            'canceled',
            'invoiced',
            'created'
        );
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1
        from pg_type t
        join pg_namespace n on n.oid = t.typnamespace
        where n.nspname = 'raw'
          and t.typname = 'payment_type_enum'
    ) then
        create type raw.payment_type_enum as enum (
            'not_defined',
            'boleto',
            'credit_card',
            'voucher',
            'debit_card'
        );
    end if;
end
$$;

create table if not exists raw.orders (
    order_id varchar(32),
    customer_id varchar(32),
    order_status raw.order_status_enum,
    order_purchase_timestamp timestamp,
    order_approved_at timestamp,
    order_delivered_carrier_date timestamp,
    order_delivered_customer_date timestamp,
    order_estimated_delivery_date timestamp
);

create table if not exists raw.order_items (
    order_id varchar(32),
    order_item_id bigint,
    product_id varchar(32),
    seller_id varchar(32),
    shipping_limit_date timestamp,
    price numeric(8, 2),
    freight_value numeric(8, 2)
);

create table if not exists raw.order_payments (
    order_id varchar(32),
    payment_sequential integer,
    payment_type raw.payment_type_enum,
    payment_installments integer,
    payment_value numeric(8, 2)
);

create table if not exists raw.order_reviews (
    review_id varchar(32),
    order_id varchar(32),
    review_score smallint check (review_score between 1 and 5),
    review_creation_date timestamp,
    review_answer_timestamp timestamp,
    review_comment_title varchar,
    review_comment_message varchar
);

create table if not exists raw.customers (
    customer_id varchar(32),
    customer_unique_id varchar(32),
    customer_zip_code_prefix integer,
    customer_city varchar,
    customer_state varchar(2)
);

create table if not exists raw.products (
    product_id varchar(32),
    product_category_name varchar,
    product_name_lenght smallint,
    product_description_lenght smallint,
    product_photos_qty smallint,
    product_weight_g integer,
    product_length_cm integer,
    product_height_cm integer,
    product_width_cm integer
);

create table if not exists raw.sellers (
    seller_id varchar(32),
    seller_zip_code_prefix integer,
    seller_city varchar,
    seller_state varchar(2)
);

create table if not exists raw.category_translation (
    product_category_name varchar,
    product_category_name_english varchar
);

create table if not exists raw.geolocation (
    geolocation_zip_code_prefix integer,
    geolocation_lat numeric,
    geolocation_lng numeric,
    geolocation_city varchar,
    geolocation_state varchar(2)
);
