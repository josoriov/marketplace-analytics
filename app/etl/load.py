"""Reload raw PostgreSQL tables in bounded batches."""

import logging
import re

import polars as pl
from psycopg2.extras import execute_values
from sqlalchemy.engine import Engine

from app.core.database import get_engine
from app.etl.config import INGESTION_CONFIGS, IngestionConfig

logger = logging.getLogger(__name__)
DEFAULT_CHUNK_SIZE = 5_000
_SAFE_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*", re.IGNORECASE)


def load_dataset(
    df: pl.DataFrame,
    config: IngestionConfig,
    engine: Engine,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> int:
    """Truncate and insert atomically; preserve the old table if loading fails."""
    qualified = _validated_table_name(config.destination_table)
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    columns = [col for col in config.expected_columns if col in df.columns]
    df = df.select(columns)
    if any(not _SAFE_IDENTIFIER.fullmatch(col) for col in columns):
        raise ValueError("Invalid column identifier")
    with engine.begin() as connection, connection.connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {qualified}")
        for chunk in df.iter_slices(chunk_size):
            execute_values(
                cursor, f"INSERT INTO {qualified} ({', '.join(columns)}) VALUES %s",
                chunk.rows(), page_size=chunk_size,
            )
    logger.info("Loaded %d row(s) into %s", df.height, qualified)
    return df.height


def load_all(datasets: dict[str, pl.DataFrame]) -> dict[str, int]:
    engine = get_engine()
    return {
        INGESTION_CONFIGS[filename].destination_table: load_dataset(df, INGESTION_CONFIGS[filename], engine)
        for filename, df in datasets.items()
    }


def _validated_table_name(destination_table: str) -> str:
    parts = destination_table.split(".")
    if len(parts) != 2 or not all(_SAFE_IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(f"Invalid table identifier: {destination_table!r}")
    return destination_table
