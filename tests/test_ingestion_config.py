from app.etl.config import INGESTION_CONFIGS


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
    assert {config.destination_table for config in INGESTION_CONFIGS.values()} == {
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
    config = INGESTION_CONFIGS["olist_orders_dataset.csv"]

    assert config.destination_table == "raw.orders"
    assert config.primary_key_columns == ("order_id",)


def test_item_config_has_required_columns():
    assert INGESTION_CONFIGS["olist_order_items_dataset.csv"].expected_columns == (
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    )
