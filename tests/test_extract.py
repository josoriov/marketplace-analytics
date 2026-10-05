import pytest

from app.etl.extract import (
    ExtractionWarning,
    extract_dataset,
    extract_datasets,
    validate_required_csv_files,
)


def test_extract_dataset_normalizes_headers_and_can_trim_strings(tmp_path) -> None:
    csv_path = tmp_path / "olist_orders_dataset.csv"
    csv_path.write_text(
        (
            " ORDER_ID , CUSTOMER_ID , ORDER_STATUS \n"
            " order-1 , customer-1 , delivered \n"
        ),
        encoding="utf-8",
    )

    dataframe = extract_dataset(
        "olist_orders_dataset.csv",
        data_dir=tmp_path,
        trim_string_columns=True,
    )

    assert dataframe.columns == ["order_id", "customer_id", "order_status"]
    assert dataframe.row(0) == ("order-1", "customer-1", "delivered")


def test_extract_dataset_warns_for_empty_csv(tmp_path) -> None:
    csv_path = tmp_path / "olist_sellers_dataset.csv"
    csv_path.write_text(
        "seller_id,seller_zip_code_prefix,seller_city,seller_state\n",
        encoding="utf-8",
    )

    with pytest.warns(ExtractionWarning, match="is empty"):
        dataframe = extract_dataset("olist_sellers_dataset.csv", data_dir=tmp_path)

    assert dataframe.is_empty()


def test_extract_dataset_warns_for_unexpected_columns(tmp_path) -> None:
    csv_path = tmp_path / "olist_customers_dataset.csv"
    csv_path.write_text(
        (
            "customer_id,customer_unique_id,customer_zip_code_prefix,"
            "customer_city,customer_state,debug_column\n"
            "c1,u1,12345,berlin,BE,extra\n"
        ),
        encoding="utf-8",
    )

    with pytest.warns(ExtractionWarning, match="unexpected columns: debug_column"):
        dataframe = extract_dataset("olist_customers_dataset.csv", data_dir=tmp_path)

    assert "debug_column" in dataframe.columns


def test_validate_required_csv_files_lists_missing_files(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="olist_orders_dataset.csv"):
        validate_required_csv_files(["olist_orders_dataset.csv"], data_dir=tmp_path)


def test_extract_datasets_fails_fast_when_any_required_file_is_missing(tmp_path) -> None:
    orders_csv = tmp_path / "olist_orders_dataset.csv"
    orders_csv.write_text(
        "order_id,customer_id,order_status\norder-1,customer-1,delivered\n",
        encoding="utf-8",
    )

    with pytest.raises(
        FileNotFoundError,
        match="olist_order_items_dataset.csv",
    ):
        extract_datasets(
            [
                "olist_orders_dataset.csv",
                "olist_order_items_dataset.csv",
            ],
            data_dir=tmp_path,
        )


def test_extract_rejects_headers_that_normalize_to_the_same_name(tmp_path):
    (tmp_path / "olist_orders_dataset.csv").write_text("order_id, ORDER_ID \no1,o2\n")
    with pytest.raises(ValueError, match="duplicate names: order_id"):
        extract_dataset("olist_orders_dataset.csv", data_dir=tmp_path)
