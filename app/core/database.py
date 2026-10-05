"""Shared engine and transactional SQL execution."""

from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from app.core.config import PROJECT_ROOT, get_settings

SQL_SCRIPTS_DIR = PROJECT_ROOT / "app" / "db"


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_connection() -> Connection:
    return get_engine().connect()


def run_sql_script(script_path: str | Path) -> None:
    """Run a complete PostgreSQL script; roll back on failure."""
    sql = _resolve_sql_path(script_path).read_text(encoding="utf-8-sig")
    with get_engine().begin() as connection:
        connection.exec_driver_sql(sql)


def test_connection() -> int:
    with get_connection() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()


def _resolve_sql_path(script_path: str | Path) -> Path:
    """Accept absolute, project-relative, or app/db-relative script paths."""
    path = Path(script_path)
    for candidate in (PROJECT_ROOT / path, SQL_SCRIPTS_DIR / path):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"SQL script does not exist: {script_path}")
