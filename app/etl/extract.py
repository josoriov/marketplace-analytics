"""Read and normalize the configured Olist CSV files."""

import warnings
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import polars as pl

from app.etl.config import INGESTION_CONFIGS, RAW_DATA_DIR


class ExtractionWarning(UserWarning):
    """Non-fatal CSV extraction issue."""


def extract_dataset(
    csv_filename: str,
    *,
    data_dir: str | Path | None = None,
    trim_string_columns: bool = False,
) -> pl.DataFrame:
    config = INGESTION_CONFIGS[csv_filename]
    path = (Path(data_dir) if data_dir is not None else RAW_DATA_DIR) / csv_filename
    df = pl.read_csv(path, raise_if_empty=False)
    columns = [column.strip().lower() for column in df.columns]
    duplicates = sorted(name for name, count in Counter(columns).items() if count > 1)
    if duplicates:
        raise ValueError(f"Column normalization created duplicate names: {', '.join(duplicates)}")
    df.columns = columns
    if trim_string_columns:
        df = df.with_columns(pl.col(pl.String).str.strip_chars())
    if df.is_empty():
        warnings.warn(
            f"{csv_filename} is empty and loaded no rows into {config.destination_table}",
            ExtractionWarning, stacklevel=2,
        )
    unexpected = sorted(set(df.columns) - set(config.expected_columns))
    if unexpected:
        warnings.warn(
            f"{csv_filename} includes unexpected columns: {', '.join(unexpected)}",
            ExtractionWarning, stacklevel=2,
        )
    return df


def validate_required_csv_files(
    csv_filenames: Iterable[str] | None = None,
    *,
    data_dir: str | Path | None = None,
) -> None:
    filenames = INGESTION_CONFIGS if csv_filenames is None else csv_filenames
    base_dir = Path(data_dir) if data_dir is not None else RAW_DATA_DIR
    missing = []
    for filename in filenames:
        INGESTION_CONFIGS[filename]  # Reject unknown datasets before reading files.
        if not (base_dir / filename).is_file():
            missing.append(filename)
    if missing:
        raise FileNotFoundError(f"Missing required CSV file(s): {', '.join(missing)}")


def extract_datasets(
    csv_filenames: Iterable[str] | None = None,
    *,
    data_dir: str | Path | None = None,
    trim_string_columns: bool = False,
) -> dict[str, pl.DataFrame]:
    filenames = tuple(INGESTION_CONFIGS if csv_filenames is None else csv_filenames)
    validate_required_csv_files(filenames, data_dir=data_dir)
    return {
        filename: extract_dataset(filename, data_dir=data_dir, trim_string_columns=trim_string_columns)
        for filename in filenames
    }
