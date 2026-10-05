from app.etl.config import (
    INGESTION_CONFIGS,
    RAW_DATA_DIR,
    TABLE_INGESTION_CONFIGS,
    get_ingestion_config,
    get_ingestion_config_by_table,
    iter_ingestion_configs,
)


def test_ingestion_configs_cover_each_raw_dataset() -> None:
    assert set(INGESTION_CONFIGS) == {
        "olist_customers_dataset.csv",
        "olist_geolocation_dataset.csv",
        "olist_order_items_dataset.csv",
        "olist_order_payments_dataset.csv",
        "olist_order_reviews_dataset.csv",
        "olist_orders_dataset.csv",
        "olist_products_dataset.csv",
        "olist_sellers_dataset.csv",
        "product_category_name_translation.csv",
    }
    assert {config.destination_table for config in iter_ingestion_configs()} == {
        "raw.category_translation",
        "raw.customers",
        "raw.geolocation",
        "raw.order_items",
        "raw.order_payments",
        "raw.order_reviews",
        "raw.orders",
        "raw.products",
        "raw.sellers",
    }


def test_orders_ingestion_config_contains_expected_metadata() -> None:
    config = get_ingestion_config("olist_orders_dataset.csv")

    assert config.destination_table == "raw.orders"
    assert config.date_columns == (
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    )
    assert config.primary_key_columns == ("order_id",)
    assert config.csv_path == RAW_DATA_DIR / "olist_orders_dataset.csv"


def test_table_lookup_reuses_the_same_config_objects() -> None:
    by_file = get_ingestion_config("olist_order_items_dataset.csv")
    by_table = get_ingestion_config_by_table("raw.order_items")

    assert by_table is by_file
    assert TABLE_INGESTION_CONFIGS["raw.order_items"].expected_columns == (
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    )
