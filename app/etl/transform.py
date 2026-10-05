"""Run the locked dbt v2 binary with the application environment."""

import subprocess
import sys
from pathlib import Path

from app.core.config import PROJECT_ROOT, get_settings


def run_dbt(*args: str) -> None:
    get_settings()  # Validate the same connection variables as ingestion.
    subprocess.run(
        [
            str(Path(sys.executable).with_name("dbt")), *args,
            "--project-dir", str(PROJECT_ROOT / "dbt"),
            "--profiles-dir", str(PROJECT_ROOT / "dbt"),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


if __name__ == "__main__":
    try:
        run_dbt(*(sys.argv[1:] or ["build"]))
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
