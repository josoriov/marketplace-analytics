import polars as pl
import pytest

from app.etl.config import IngestionConfig
from app.etl.validators import (
    ValidationReport,
    validate_all,
    validate_dataframe,
)


def _make_config(
    filename: str = "test.csv",
    table: str = "raw.test",
    columns: tuple[str, ...] = ("a", "b"),
    date_columns: tuple[str, ...] = (),
    pk_columns: tuple[str, ...] = (),
) -> IngestionConfig:
    return IngestionConfig(
        csv_filename=filename,
        destination_table=table,
        expected_columns=columns,
        date_columns=date_columns,
        primary_key_columns=pk_columns,
    )


# ── ValidationReport ─────────────────────────────────────────────────


class TestValidationReport:
    def test_passed_when_no_errors(self) -> None:
        report = ValidationReport()
        report.add_warning("t", "c", "msg")
        assert report.passed is True

    def test_failed_when_errors_exist(self) -> None:
        report = ValidationReport()
        report.add_error("t", "c", "msg")
        assert report.passed is False

    def test_errors_and_warnings_are_separated(self) -> None:
        report = ValidationReport()
        report.add_error("t", "e1", "err")
        report.add_warning("t", "w1", "warn")
        assert len(report.errors) == 1
        assert len(report.warnings) == 1


# ── Required columns ─────────────────────────────────────────────────


class TestCheckRequiredColumns:
    def test_reports_error_for_missing_columns(self) -> None:
        config = _make_config(columns=("a", "b", "c"))
        df = pl.DataFrame({"a": [1], "b": [2]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert any(
            i.check == "missing_columns" and i.severity == "error"
            for i in report.issues
        )

    def test_no_error_when_all_columns_present(self) -> None:
        config = _make_config(columns=("a", "b"))
        df = pl.DataFrame({"a": [1], "b": [2]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "missing_columns" for i in report.issues)


# ── Duplicate primary keys ───────────────────────────────────────────


class TestCheckDuplicatePrimaryKeys:
    def test_warns_on_duplicates(self) -> None:
        config = _make_config(columns=("id", "val"), pk_columns=("id",))
        df = pl.DataFrame({"id": [1, 1, 2], "val": ["a", "b", "c"]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert any(
            i.check == "duplicate_primary_keys" and i.severity == "warning"
            for i in report.issues
        )

    def test_no_warning_when_unique(self) -> None:
        config = _make_config(columns=("id", "val"), pk_columns=("id",))
        df = pl.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "duplicate_primary_keys" for i in report.issues)


# ── Negative monetary values ─────────────────────────────────────────


class TestCheckNegativeMonetaryValues:
    def test_errors_on_negative_price(self) -> None:
        config = _make_config(
            table="raw.order_items",
            columns=("price", "freight_value"),
        )
        df = pl.DataFrame({"price": [-10.0], "freight_value": [5.0]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        errors = [i for i in report.issues if i.check == "negative_monetary"]
        assert len(errors) == 1
        assert "price" in errors[0].message

    def test_errors_on_negative_freight_value(self) -> None:
        config = _make_config(
            table="raw.order_items",
            columns=("price", "freight_value"),
        )
        df = pl.DataFrame({"price": [10.0], "freight_value": [-3.0]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        errors = [i for i in report.issues if i.check == "negative_monetary"]
        assert len(errors) == 1
        assert "freight_value" in errors[0].message

    def test_no_error_for_positive_values(self) -> None:
        config = _make_config(
            table="raw.order_items",
            columns=("price", "freight_value"),
        )
        df = pl.DataFrame({"price": [10.0], "freight_value": [5.0]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "negative_monetary" for i in report.issues)


# ── Bounded columns ──────────────────────────────────────────────────


class TestCheckBoundedColumns:
    def test_errors_on_review_score_out_of_bounds(self) -> None:
        config = _make_config(
            table="raw.order_reviews",
            columns=("review_id", "order_id", "review_score",
                     "review_comment_title", "review_comment_message",
                     "review_creation_date", "review_answer_timestamp"),
            pk_columns=("review_id",),
        )
        df = pl.DataFrame({
            "review_id": ["r1", "r2"],
            "order_id": ["o1", "o2"],
            "review_score": [0, 6],
            "review_comment_title": [None, None],
            "review_comment_message": [None, None],
            "review_creation_date": [None, None],
            "review_answer_timestamp": [None, None],
        })
        report = ValidationReport()

        validate_dataframe(df, config, report)

        errors = [i for i in report.issues if i.check == "out_of_bounds"]
        assert len(errors) == 1
        assert "2 row(s)" in errors[0].message

    def test_valid_scores_pass(self) -> None:
        config = _make_config(
            table="raw.order_reviews",
            columns=("review_id", "review_score"),
            pk_columns=("review_id",),
        )
        df = pl.DataFrame({"review_id": ["r1", "r2"], "review_score": [1, 5]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "out_of_bounds" for i in report.issues)


# ── Date ordering ────────────────────────────────────────────────────


class TestCheckDateOrdering:
    def test_warns_when_delivery_precedes_purchase(self) -> None:
        config = _make_config(
            table="raw.orders",
            columns=("order_id", "order_purchase_timestamp",
                     "order_delivered_customer_date"),
            date_columns=("order_purchase_timestamp",
                          "order_delivered_customer_date"),
            pk_columns=("order_id",),
        )
        df = pl.DataFrame({
            "order_id": ["o1"],
            "order_purchase_timestamp": ["2020-06-01 10:00:00"],
            "order_delivered_customer_date": ["2020-05-01 10:00:00"],
        })
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert any(
            i.check == "date_ordering" and i.severity == "warning"
            for i in report.issues
        )

    def test_no_warning_for_correct_date_order(self) -> None:
        config = _make_config(
            table="raw.orders",
            columns=("order_id", "order_purchase_timestamp",
                     "order_delivered_customer_date"),
            date_columns=("order_purchase_timestamp",
                          "order_delivered_customer_date"),
            pk_columns=("order_id",),
        )
        df = pl.DataFrame({
            "order_id": ["o1"],
            "order_purchase_timestamp": ["2020-05-01 10:00:00"],
            "order_delivered_customer_date": ["2020-06-01 10:00:00"],
        })
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "date_ordering" for i in report.issues)

    def test_skips_when_both_dates_are_null(self) -> None:
        config = _make_config(
            table="raw.orders",
            columns=("order_id", "order_purchase_timestamp",
                     "order_delivered_customer_date"),
            date_columns=("order_purchase_timestamp",
                          "order_delivered_customer_date"),
            pk_columns=("order_id",),
        )
        df = pl.DataFrame({
            "order_id": ["o1"],
            "order_purchase_timestamp": [None],
            "order_delivered_customer_date": [None],
        })
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "date_ordering" for i in report.issues)


# ── Null-heavy columns ──────────────────────────────────────────────


class TestCheckNullHeavyColumns:
    def test_warns_on_mostly_null_column(self) -> None:
        config = _make_config(columns=("a", "b"))
        df = pl.DataFrame({"a": [1, 2, 3, 4], "b": [None, None, None, "x"]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        null_warnings = [i for i in report.issues if i.check == "null_heavy_column"]
        assert len(null_warnings) == 1
        assert "b" in null_warnings[0].message

    def test_no_warning_when_below_threshold(self) -> None:
        config = _make_config(columns=("a", "b"))
        df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", None]})
        report = ValidationReport()

        validate_dataframe(df, config, report)

        assert not any(i.check == "null_heavy_column" for i in report.issues)


# ── validate_all integration ─────────────────────────────────────────


class TestValidateAll:
    def test_warns_on_unknown_filename(self) -> None:
        datasets = {"unknown_file.csv": pl.DataFrame({"x": [1]})}
        report = validate_all(datasets)

        assert any(i.check == "config_lookup" for i in report.issues)

    def test_runs_checks_for_known_dataset(self) -> None:
        datasets = {
            "olist_orders_dataset.csv": pl.DataFrame({
                "order_id": ["o1"],
                "customer_id": ["c1"],
            }),
        }
        report = validate_all(datasets)

        # Should flag missing columns (many are absent)
        assert any(i.check == "missing_columns" for i in report.issues)
