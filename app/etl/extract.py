"""CSV extraction helpers for the raw Olist ingestion pipeline."""

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
import warnings

import polars as pl

from app.etl.config import (
    RAW_DATA_DIR,
    IngestionConfig,
    get_ingestion_config,
    iter_ingestion_configs,
)


class ExtractionWarning(UserWarning):
    """Warning raised for non-fatal issues discovered during CSV extraction."""


def extract_dataset(
    csv_filename: str,
    *,
    data_dir: str | Path | None = None,
    trim_string_columns: bool = False,
) -> pl.DataFrame:
    """Load a configured CSV into a normalized Polars DataFrame.

    Args:
        csv_filename: Configured CSV filename to load.
        data_dir: Optional base directory for raw CSV files. Defaults to
            ``data/raw`` inside the project.
        trim_string_columns: When ``True``, strip surrounding whitespace from
            every string column after the CSV is loaded.

    Returns:
        pl.DataFrame: The loaded DataFrame with normalized lowercase columns.

    Raises:
        FileNotFoundError: If the configured CSV file does not exist.
        KeyError: If the CSV filename is not present in the ingestion config.
        ValueError: If column normalization would create duplicate names.
    """
    config = get_ingestion_config(csv_filename)
    csv_path = _resolve_csv_path(config, data_dir)

    dataframe = pl.read_csv(csv_path, raise_if_empty=False)
    dataframe = _normalize_dataframe_columns(dataframe)

    if trim_string_columns:
        dataframe = _trim_string_columns(dataframe)

    _warn_if_empty(dataframe, config)
    _warn_on_unexpected_columns(dataframe, config)

    return dataframe


def extract_datasets(
    csv_filenames: Iterable[str] | None = None,
    *,
    data_dir: str | Path | None = None,
    trim_string_columns: bool = False,
) -> dict[str, pl.DataFrame]:
    """Load multiple configured CSVs and return them keyed by filename.

    Args:
        csv_filenames: Optional subset of configured CSV filenames. When
            omitted, every configured raw dataset is loaded.
        data_dir: Optional base directory for raw CSV files. Defaults to
            ``data/raw`` inside the project.
        trim_string_columns: When ``True``, strip surrounding whitespace from
            every string column after each CSV is loaded.

    Returns:
        dict[str, pl.DataFrame]: Loaded DataFrames keyed by their CSV filename.

    Raises:
        FileNotFoundError: If any required CSV file is missing.
    """
    configs = _resolve_configs(csv_filenames)
    validate_required_csv_files(
        (config.csv_filename for config in configs),
        data_dir=data_dir,
    )

    return {
        config.csv_filename: extract_dataset(
            config.csv_filename,
            data_dir=data_dir,
            trim_string_columns=trim_string_columns,
        )
        for config in configs
    }


def validate_required_csv_files(
    csv_filenames: Iterable[str] | None = None,
    *,
    data_dir: str | Path | None = None,
) -> None:
    """Fail fast when any required CSV file is missing from disk.

    Args:
        csv_filenames: Optional subset of configured CSV filenames to validate.
            When omitted, every configured raw dataset is required.
        data_dir: Optional base directory for raw CSV files. Defaults to
            ``data/raw`` inside the project.

    Raises:
        FileNotFoundError: If one or more required CSV files are missing.
    """
    configs = _resolve_configs(csv_filenames)
    missing_paths: list[Path] = []
    for config in configs:
        csv_path = _build_csv_path(config, data_dir)
        if not csv_path.exists():
            missing_paths.append(csv_path)

    if missing_paths:
        missing_files = ", ".join(path.name for path in missing_paths)
        raise FileNotFoundError(f"Missing required CSV file(s): {missing_files}")


def _resolve_configs(csv_filenames: Iterable[str] | None) -> tuple[IngestionConfig, ...]:
    """Resolve requested CSV filenames into configured ingestion entries."""

    if csv_filenames is None:
        return iter_ingestion_configs()

    return tuple(get_ingestion_config(csv_filename) for csv_filename in csv_filenames)


def _resolve_csv_path(
    config: IngestionConfig,
    data_dir: str | Path | None,
) -> Path:
    """Return the configured CSV path and fail if the file is missing."""

    csv_path = _build_csv_path(config, data_dir)
    if csv_path.exists():
        return csv_path

    raise FileNotFoundError(
        f"Required CSV file {config.csv_filename!r} was not found at {csv_path}"
    )


def _build_csv_path(
    config: IngestionConfig,
    data_dir: str | Path | None,
) -> Path:
    """Build the filesystem path for a configured CSV."""

    base_dir = RAW_DATA_DIR if data_dir is None else Path(data_dir)
    return base_dir / config.csv_filename


def _normalize_dataframe_columns(dataframe: pl.DataFrame) -> pl.DataFrame:
    """Standardize headers to lowercase names without surrounding whitespace."""

    normalized_columns = tuple(column.strip().lower() for column in dataframe.columns)
    duplicates = [
        column_name
        for column_name, count in Counter(normalized_columns).items()
        if count > 1
    ]

    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(
            "Column normalization created duplicate names: "
            f"{duplicate_list}"
        )

    rename_mapping = {
        original: normalized
        for original, normalized in zip(dataframe.columns, normalized_columns)
        if original != normalized
    }

    if not rename_mapping:
        return dataframe

    return dataframe.rename(rename_mapping)


def _trim_string_columns(dataframe: pl.DataFrame) -> pl.DataFrame:
    """Strip surrounding whitespace from every string column."""

    string_columns = [
        column_name
        for column_name, data_type in dataframe.schema.items()
        if data_type == pl.String
    ]
    if not string_columns:
        return dataframe

    return dataframe.with_columns(
        pl.col(column_name).str.strip_chars().alias(column_name)
        for column_name in string_columns
    )


def _warn_if_empty(dataframe: pl.DataFrame, config: IngestionConfig) -> None:
    """Emit a warning when a CSV exists but does not contain any rows."""

    if dataframe.height == 0:
        warnings.warn(
            (
                f"{config.csv_filename} is empty and loaded no rows into "
                f"{config.destination_table}"
            ),
            ExtractionWarning,
            stacklevel=2,
        )


def _warn_on_unexpected_columns(
    dataframe: pl.DataFrame,
    config: IngestionConfig,
) -> None:
    """Emit a warning when a CSV contains headers outside the configured schema."""

    unexpected_columns = sorted(
        set(dataframe.columns) - set(config.expected_columns)
    )
    if unexpected_columns:
        warnings.warn(
            (
                f"{config.csv_filename} includes unexpected columns: "
                f"{', '.join(unexpected_columns)}"
            ),
            ExtractionWarning,
            stacklevel=2,
        )


__all__ = [
    "ExtractionWarning",
    "extract_dataset",
    "extract_datasets",
    "validate_required_csv_files",
]
