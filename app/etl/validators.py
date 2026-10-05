"""Data validation checks for extracted DataFrames before loading."""

import logging
from dataclasses import dataclass, field

import polars as pl

from app.etl.config import IngestionConfig, iter_ingestion_configs


logger = logging.getLogger(__name__)


# ── Result types ─────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """A single validation finding."""

    table: str
    check: str
    severity: str
    message: str


@dataclass
class ValidationReport:
    """Collects validation issues and determines pass/fail status."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, table: str, check: str, message: str) -> None:
        self.issues.append(ValidationIssue(table, check, "error", message))

    def add_warning(self, table: str, check: str, message: str) -> None:
        self.issues.append(ValidationIssue(table, check, "warning", message))

    def log_summary(self) -> None:
        for issue in self.issues:
            log_fn = logger.error if issue.severity == "error" else logger.warning
            log_fn("[%s] %s — %s", issue.table, issue.check, issue.message)

        if self.passed:
            logger.info("Validation passed with %d warning(s)", len(self.warnings))
        else:
            logger.error(
                "Validation failed: %d error(s), %d warning(s)",
                len(self.errors),
                len(self.warnings),
            )


# ── Domain-specific check configuration ──────────────────────────────

MONETARY_COLUMNS = frozenset({"price", "freight_value", "payment_value"})

DATE_ORDER_RULES: dict[str, list[tuple[str, str]]] = {
    "raw.orders": [
        ("order_purchase_timestamp", "order_delivered_customer_date"),
    ],
}

BOUNDED_COLUMNS: dict[str, dict[str, tuple[int, int]]] = {
    "raw.order_reviews": {"review_score": (1, 5)},
}

NULL_THRESHOLD = 0.5


# ── Public API ───────────────────────────────────────────────────────

def validate_dataframe(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    """Run all validation checks against a single DataFrame."""
    _check_required_columns(df, config, report)
    _check_duplicate_primary_keys(df, config, report)
    _check_negative_monetary_values(df, config, report)
    _check_bounded_columns(df, config, report)
    _check_date_ordering(df, config, report)
    _check_null_heavy_columns(df, config, report)


def validate_all(datasets: dict[str, pl.DataFrame]) -> ValidationReport:
    """Run validation across every extracted dataset and return a report."""
    report = ValidationReport()
    configs = {cfg.csv_filename: cfg for cfg in iter_ingestion_configs()}

    for filename, df in datasets.items():
        config = configs.get(filename)
        if config is None:
            report.add_warning(
                "unknown",
                "config_lookup",
                f"No ingestion config found for {filename!r}",
            )
            continue
        validate_dataframe(df, config, report)

    report.log_summary()
    return report


# ── Individual checks ────────────────────────────────────────────────

def _check_required_columns(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    missing = sorted(set(config.expected_columns) - set(df.columns))
    if missing:
        report.add_error(
            config.destination_table,
            "missing_columns",
            f"Missing required columns: {', '.join(missing)}",
        )


def _check_duplicate_primary_keys(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    pk = list(config.primary_key_columns)
    if not pk or not all(col in df.columns for col in pk):
        return

    duplicate_count = df.height - df.select(pk).unique().height
    if duplicate_count > 0:
        report.add_warning(
            config.destination_table,
            "duplicate_primary_keys",
            f"{duplicate_count} duplicate row(s) on ({', '.join(pk)})",
        )


def _check_negative_monetary_values(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    for col in sorted(MONETARY_COLUMNS & set(df.columns)):
        if not df[col].dtype.is_numeric():
            continue
        negative_count = df.filter(pl.col(col) < 0).height
        if negative_count > 0:
            report.add_error(
                config.destination_table,
                "negative_monetary",
                f"{negative_count} row(s) with negative {col}",
            )


def _check_bounded_columns(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    bounds = BOUNDED_COLUMNS.get(config.destination_table, {})
    for col, (lo, hi) in bounds.items():
        if col not in df.columns:
            continue
        out_of_bounds = df.filter(
            pl.col(col).is_not_null()
            & ((pl.col(col) < lo) | (pl.col(col) > hi))
        ).height
        if out_of_bounds > 0:
            report.add_error(
                config.destination_table,
                "out_of_bounds",
                f"{out_of_bounds} row(s) with {col} outside [{lo}, {hi}]",
            )


def _check_date_ordering(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    rules = DATE_ORDER_RULES.get(config.destination_table, [])
    for early_col, late_col in rules:
        if early_col not in df.columns or late_col not in df.columns:
            continue

        early = _as_datetime(df[early_col])
        late = _as_datetime(df[late_col])
        if early is None or late is None:
            continue

        invalid_count = (
            early.is_not_null() & late.is_not_null() & (late < early)
        ).sum()
        if invalid_count > 0:
            report.add_warning(
                config.destination_table,
                "date_ordering",
                f"{invalid_count} row(s) where {late_col} precedes {early_col}",
            )


def _check_null_heavy_columns(
    df: pl.DataFrame,
    config: IngestionConfig,
    report: ValidationReport,
) -> None:
    if df.height == 0:
        return
    for col in df.columns:
        null_count = df[col].null_count()
        null_ratio = null_count / df.height
        if null_ratio >= NULL_THRESHOLD:
            report.add_warning(
                config.destination_table,
                "null_heavy_column",
                f"Column '{col}' is {null_ratio:.0%} null ({null_count}/{df.height})",
            )


def _as_datetime(series: pl.Series) -> pl.Series | None:
    """Return *series* as a Datetime series, or ``None`` if conversion fails."""
    if series.dtype.is_temporal():
        return series
    if series.dtype == pl.String:
        try:
            return series.str.to_datetime(strict=False)
        except Exception:
            return None
    return None
