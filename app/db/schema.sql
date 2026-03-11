CREATE SCHEMA IF NOT EXISTS raw;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'raw'
          AND t.typname = 'order_status_enum'
    ) THEN
        CREATE TYPE raw.order_status_enum AS ENUM (
            'unavailable',
            'shipped',
            'approved',
            'processing',
            'delivered',
            'canceled',
            'invoiced',
            'created'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'raw'
          AND t.typname = 'payment_type_enum'
    ) THEN
        CREATE TYPE raw.payment_type_enum AS ENUM (
            'not_defined',
            'boleto',
            'credit_card',
            'voucher',
            'debit_card'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id varchar(32),
    customer_id varchar(32),
    order_status raw.order_status_enum,
    order_purchase_timestamp timestamp,
    order_approved_at timestamp,
    order_delivered_carrier_date timestamp,
    order_delivered_customer_date timestamp,
    order_estimated_delivery_date timestamp
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id varchar(32),
    order_item_id bigint,
    product_id varchar(32),
    seller_id varchar(32),
    shipping_limit_date timestamp,
    price numeric(8, 2),
    freight_value numeric(8, 2)
);

CREATE TABLE IF NOT EXISTS raw.order_payments (
    order_id varchar(32),
    payment_sequential integer,
    payment_type raw.payment_type_enum,
    payment_installments integer,
    payment_value numeric(8, 2)
);

CREATE TABLE IF NOT EXISTS raw.order_reviews (
    review_id varchar(32),
    order_id varchar(32),
    review_score smallint CHECK (review_score BETWEEN 1 AND 5),
    review_creation_date timestamp,
    review_answer_timestamp timestamp,
    review_comment_title varchar,
    review_comment_message varchar
);

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id varchar(32),
    customer_unique_id varchar(32),
    customer_zip_code_prefix integer,
    customer_city varchar,
    customer_state varchar(2)
);

CREATE TABLE IF NOT EXISTS raw.products (
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

CREATE TABLE IF NOT EXISTS raw.sellers (
    seller_id varchar(32),
    seller_zip_code_prefix integer,
    seller_city varchar,
    seller_state varchar(2)
);

CREATE TABLE IF NOT EXISTS raw.category_translation (
    product_category_name varchar,
    product_category_name_english varchar
);

CREATE TABLE IF NOT EXISTS raw.geolocation (
    geolocation_zip_code_prefix integer,
    geolocation_lat numeric,
    geolocation_lng numeric,
    geolocation_city varchar,
    geolocation_state varchar(2)
);
