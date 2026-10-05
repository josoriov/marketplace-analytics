"""Initialize the configured PostgreSQL database from a SQL script."""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import run_sql_script, test_connection


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply a SQL script to the configured PostgreSQL database."
    )
    parser.add_argument(
        "script",
        nargs="?",
        default="schema.sql",
        help="SQL script path. Defaults to schema.sql resolved from app/db/.",
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip the database connectivity check before applying the script.",
    )
    args = parser.parse_args()

    if not args.skip_check:
        test_connection()

    run_sql_script(args.script)
    print(f"Applied SQL script: {args.script}")


if __name__ == "__main__":
    main()
