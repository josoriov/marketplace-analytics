"""Central ingestion configuration for the raw Olist CSV datasets."""

from dataclasses import dataclass

from app.core.config import PROJECT_ROOT

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class IngestionConfig:
    """Describe how a raw CSV maps into a destination table."""

    csv_filename: str
    destination_table: str
    expected_columns: tuple[str, ...]
    primary_key_columns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        expected = set(self.expected_columns)
        invalid_primary_key_columns = set(self.primary_key_columns) - expected

        if invalid_primary_key_columns:
            raise ValueError(
                f"{self.csv_filename} declares unknown primary key columns: "
                f"{sorted(invalid_primary_key_columns)}"
            )


INGESTION_CONFIGS = {config.csv_filename: config for config in (
    IngestionConfig(
        csv_filename="olist_orders_dataset.csv",
        destination_table="raw.orders",
        expected_columns=(
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
        primary_key_columns=("order_id",),
    ),
    IngestionConfig(
        csv_filename="olist_order_items_dataset.csv",
        destination_table="raw.order_items",
        expected_columns=(
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
        primary_key_columns=("order_id", "order_item_id"),
    ),
    IngestionConfig(
        csv_filename="olist_order_payments_dataset.csv",
        destination_table="raw.order_payments",
        expected_columns=(
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
        primary_key_columns=("order_id", "payment_sequential"),
    ),
    IngestionConfig(
        csv_filename="olist_order_reviews_dataset.csv",
        destination_table="raw.order_reviews",
        expected_columns=(
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
        primary_key_columns=("review_id",),
    ),
    IngestionConfig(
        csv_filename="olist_customers_dataset.csv",
        destination_table="raw.customers",
        expected_columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
        primary_key_columns=("customer_id",),
    ),
    IngestionConfig(
        csv_filename="olist_products_dataset.csv",
        destination_table="raw.products",
        expected_columns=(
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
        primary_key_columns=("product_id",),
    ),
    IngestionConfig(
        csv_filename="olist_sellers_dataset.csv",
        destination_table="raw.sellers",
        expected_columns=(
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ),
        primary_key_columns=("seller_id",),
    ),
    IngestionConfig(
        csv_filename="product_category_name_translation.csv",
        destination_table="raw.category_translation",
        expected_columns=(
            "product_category_name",
            "product_category_name_english",
        ),
        primary_key_columns=("product_category_name",),
    ),
    IngestionConfig(
        csv_filename="olist_geolocation_dataset.csv",
        destination_table="raw.geolocation",
        expected_columns=(
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
    ),
)}
