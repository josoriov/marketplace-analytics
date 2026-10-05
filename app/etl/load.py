"""Load extracted DataFrames into PostgreSQL raw tables."""

import logging
import re

import polars as pl
from psycopg2.extras import execute_values
from sqlalchemy.engine import Engine

from app.core.database import get_engine
from app.etl.config import IngestionConfig, iter_ingestion_configs


logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 5_000
_SAFE_IDENTIFIER = re.compile(r"^[a-z_]\w*$")


def load_dataset(
    df: pl.DataFrame,
    config: IngestionConfig,
    engine: Engine,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> int:
    """Truncate and reload a single DataFrame into its destination table.

    Returns the number of rows loaded.
    """
    qualified = _validated_table_name(config.destination_table)
    columns = [col for col in config.expected_columns if col in df.columns]
    df_to_load = df.select(columns)

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.execute(f"TRUNCATE TABLE {qualified}")

        if df_to_load.height == 0:
            raw_conn.commit()
            logger.info("Skipped %s — 0 rows", qualified)
            return 0

        col_list = ", ".join(columns)
        insert_sql = f"INSERT INTO {qualified} ({col_list}) VALUES %s"

        rows_loaded = 0
        for offset in range(0, df_to_load.height, chunk_size):
            chunk_rows = df_to_load.slice(offset, chunk_size).rows()
            execute_values(cursor, insert_sql, chunk_rows, page_size=chunk_size)
            rows_loaded += len(chunk_rows)

        raw_conn.commit()
        logger.info("Loaded %d row(s) into %s", rows_loaded, qualified)
        return rows_loaded
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def load_all(datasets: dict[str, pl.DataFrame]) -> dict[str, int]:
    """Load every extracted dataset into its destination table.

    Returns a mapping of table name to rows loaded.
    """
    engine = get_engine()
    configs = {cfg.csv_filename: cfg for cfg in iter_ingestion_configs()}
    row_counts: dict[str, int] = {}

    for filename, df in datasets.items():
        config = configs[filename]
        row_counts[config.destination_table] = load_dataset(df, config, engine)

    total = sum(row_counts.values())
    logger.info("Total: %d row(s) across %d table(s)", total, len(row_counts))
    return row_counts


def _validated_table_name(destination_table: str) -> str:
    """Validate and return a ``schema.table`` identifier.

    Raises ValueError if the name doesn't match the expected pattern.
    """
    parts = destination_table.split(".")
    if len(parts) != 2 or not all(_SAFE_IDENTIFIER.match(p) for p in parts):
        raise ValueError(f"Invalid table identifier: {destination_table!r}")
    return destination_table
