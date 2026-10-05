"""End-to-end ETL pipeline orchestrator.

Run with::

    python -m app.etl.pipeline
"""

import logging
import sys

from app.core.database import run_sql_script, test_connection
from app.etl.extract import extract_datasets
from app.etl.load import load_all
from app.etl.validators import validate_all


logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """Execute the full extract → validate → load → transform → verify pipeline."""
    _configure_logging()

    logger.info("Starting ETL pipeline")

    logger.info("Step 1/8 — Testing database connection")
    test_connection()

    logger.info("Step 2/8 — Applying raw database schema")
    run_sql_script("schema.sql")

    logger.info("Step 3/8 — Extracting CSV datasets")
    datasets = extract_datasets(trim_string_columns=True)

    logger.info("Step 4/8 — Validating extracted data")
    report = validate_all(datasets)
    if not report.passed:
        logger.error("Validation failed — aborting pipeline")
        sys.exit(1)

    logger.info("Step 5/8 — Loading raw data into Postgres")
    load_all(datasets)

    logger.info("Step 6/8 — Creating performance indexes")
    run_sql_script("indexes.sql")

    logger.info("Step 7/8 — Building analytics models")
    run_sql_script("marts.sql")

    logger.info("Step 8/8 — Running sanity checks on analytics layer")
    run_sql_script("sanity_checks.sql")

    logger.info("Pipeline finished successfully")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    run_pipeline()
