"""Extract, validate, load, and build/test analytics with dbt."""

import logging
import subprocess
import sys

from app.core.database import run_sql_script, test_connection
from app.etl.extract import extract_datasets
from app.etl.load import load_all
from app.etl.transform import run_dbt
from app.etl.validators import validate_all

logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """Execute the full extract → validate → load → transform → verify pipeline."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("Starting ETL pipeline")

    logger.info("Step 1/7 — Testing database connection")
    test_connection()

    logger.info("Step 2/7 — Applying raw database schema")
    run_sql_script("schema.sql")

    logger.info("Step 3/7 — Extracting CSV datasets")
    datasets = extract_datasets()

    logger.info("Step 4/7 — Validating extracted data")
    report = validate_all(datasets)
    if not report.passed:
        logger.error("Validation failed — aborting pipeline")
        sys.exit(1)

    logger.info("Step 5/7 — Loading raw data into Postgres")
    load_all(datasets)

    logger.info("Step 6/7 — Creating performance indexes")
    run_sql_script("indexes.sql")

    logger.info("Step 7/7 — Building and testing silver/gold models with dbt")
    run_dbt("build")

    logger.info("Pipeline finished successfully")

if __name__ == "__main__":
    try:
        run_pipeline()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
